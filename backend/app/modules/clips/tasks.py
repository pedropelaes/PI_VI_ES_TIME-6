"""Tasks Celery de processamento de vídeo (rodam no worker, com torch/GPU).

Movidas de `router.py`. O import de `ml` é feito DENTRO da task (lazy), então a
API pode importar este módulo (para publicar via `.delay()`) sem puxar torch.
"""
from pathlib import Path
import time
import traceback
import uuid
from datetime import datetime, timezone, timedelta

from celery.signals import worker_ready

from app.celery_app import celery_app
from app.core.security import decrypt_drive_token
from app.core.storage import get_storage
from app.modules.clips.models import ProcessingJob, Clip, Candidate
from app.modules.clips.video_utils import ensure_h264

# Resolve pela abstracao de storage (§4.2): o worker precisa gravar na MESMA
# raiz de uploads que a API serve via StaticFiles. Caminho relativo a __file__
# apontava um nivel fundo demais e deixava os clipes fora do volume montado.
CLIPS_DIR = get_storage().path_for("clips")
CLIPS_DIR.mkdir(parents=True, exist_ok=True)
VIDEOS_DIR = get_storage().path_for("videos")
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


def update_job_status(job_id: uuid.UUID, status: str):
    """Atualiza o status do job no DB de forma isolada."""
    from app.core.database import get_session
    session = next(get_session())
    try:
        job = session.get(ProcessingJob, job_id)
        if job:
            job.status = status
            job.updated_at = datetime.now(timezone.utc)
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"[db error] Falha ao atualizar status: {e}")
    finally:
        session.close()


def _get_job_status(job_id: uuid.UUID) -> str | None:
    """Consulta o status atual do job no DB de forma isolada."""
    from app.core.database import get_session
    session = next(get_session())
    try:
        job = session.get(ProcessingJob, job_id)
        return job.status if job else None
    finally:
        session.close()


def _resolve_video_path(job_id: uuid.UUID, fallback_path: str) -> str:
    """Resolve o caminho atual do vídeo (útil em retries após conversão para H.264)."""
    if fallback_path and Path(fallback_path).exists():
        return fallback_path

    from app.core.database import get_session
    from app.modules.clips.models import Video
    session = next(get_session())
    try:
        job = session.get(ProcessingJob, job_id)
        if job:
            video = session.get(Video, job.video_id)
            if video and video.storage_path:
                return video.storage_path
    finally:
        session.close()
    return fallback_path


def normalize_job_video(job_id: uuid.UUID, video_path: str) -> str:
    """Garante H.264 e atualiza o caminho do vídeo no banco se convertido."""
    from app.core.database import get_session
    from app.modules.clips.models import Video

    new_path = ensure_h264(
        Path(video_path),
        on_converting=lambda: update_job_status(job_id, "CONVERTING"),
    )
    if str(new_path) == video_path:
        return video_path

    session = next(get_session())
    try:
        job = session.get(ProcessingJob, job_id)
        if job:
            video = session.get(Video, job.video_id)
            if video:
                video.storage_path = str(new_path)
                video.file_size_mb = round(new_path.stat().st_size / (1024 * 1024), 2)
                session.add(video)
                session.commit()
    finally:
        session.close()
    return str(new_path)


def _retry_or_fail(task_self, job_id: uuid.UUID, exc: Exception) -> None:
    """Reagenda falhas transitórias no worker e marca ERROR somente em falha definitiva."""
    from app.core.exceptions import (
        BadRequestError,
        ForbiddenError,
        NotFoundError,
        UnauthorizedError,
    )

    definitive_errors = (
        UnauthorizedError,
        ForbiddenError,
        NotFoundError,
        BadRequestError,
    )
    in_worker = not getattr(task_self.request, "called_directly", True)
    retries = getattr(task_self.request, "retries", 0)
    max_retries = getattr(task_self, "max_retries", 0) or 0

    if in_worker and not isinstance(exc, definitive_errors) and retries < max_retries:
        countdown = 5 * (2 ** retries)
        print(
            f"[RETRY] Job {job_id} falhou ({exc}). "
            f"Tentativa {retries + 1}/{max_retries} em {countdown}s."
        )
        raise task_self.retry(exc=exc, countdown=countdown)

    update_job_status(job_id, "ERROR")
    if in_worker and "CUDA" in str(exc):
        raise exc


def _make_save_candidate_callback(job_id: uuid.UUID, target_number: int):
    def save_candidate_to_db(cand_dict):
        from app.core.database import get_session
        from sqlmodel import select
        session = next(get_session())
        try:
            existing = session.exec(
                select(Candidate).where(
                    Candidate.job_id == job_id,
                    Candidate.signature == cand_dict["id"],
                )
            ).first()
            if existing:
                return

            novo_candidato = Candidate(
                job_id=job_id,
                signature=cand_dict["id"],
                name=cand_dict["name"],
                number=cand_dict["number"],
                color_hex=cand_dict["color"],
                image_path=cand_dict["image"],
                is_target=(cand_dict["number"] == target_number),
            )
            session.add(novo_candidato)
            job = session.get(ProcessingJob, job_id)
            if job:
                job.updated_at = datetime.now(timezone.utc)
            session.commit()
        except Exception as e:
            print(f"[DB ERROR] Erro ao salvar candidato: {e}")
            session.rollback()
        finally:
            session.close()

    return save_candidate_to_db


def _make_check_stop_callback(job_id: uuid.UUID, expected_status: str):
    def check_stop():
        from app.core.database import get_session
        session = next(get_session())
        try:
            job = session.get(ProcessingJob, job_id)
            if not job:
                return True
            return job.status != expected_status
        finally:
            session.close()

    return check_stop


def _clear_partial_clips(job_id: uuid.UUID) -> None:
    """Remove clipes parciais anteriores do job antes de reexecutar o tracking."""
    from app.core.database import get_session
    from sqlmodel import select
    session = next(get_session())
    storage = get_storage()
    try:
        existing_clips = session.exec(select(Clip).where(Clip.job_id == job_id)).all()
        if not existing_clips:
            return
        for clip in existing_clips:
            if clip.storage_path:
                storage.delete(clip.storage_path)
            session.delete(clip)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[db error] Falha ao limpar clipes parciais do job {job_id}: {e}")
    finally:
        session.close()


def _execute_scan_stage(
    task_self,
    job_id: uuid.UUID,
    video_path: str,
    target_number: int,
    start_ts: int,
    end_ts: int,
    stage_status: str,
    allowed_initial_statuses: tuple[str, ...],
    frames_to_skip: int,
) -> None:
    """Executa Fast Scan ou Deep Scan de forma idempotente com retry e retomada."""
    current_status = _get_job_status(job_id)
    if current_status is not None and current_status not in allowed_initial_statuses:
        print(f"[{stage_status}] Ignorando job {job_id} no estado {current_status}.")
        return

    print(f"[{stage_status}] Iniciando job {job_id}")
    update_job_status(job_id, stage_status)

    try:
        resolved_path = _resolve_video_path(job_id, video_path)
        # Converte para H.264 se o vídeo vier em AV1/VP9/etc (OpenCV não decodifica)
        normalized_path = normalize_job_video(job_id, resolved_path)
        if normalized_path != resolved_path or _get_job_status(job_id) == "CONVERTING":
            update_job_status(job_id, stage_status)

        from ml.scripts.process_video import _get_pipeline
        pipeline = _get_pipeline()
        output_dir = str(CLIPS_DIR / str(job_id))

        pipeline.fast_scan(
            video_path=normalized_path,
            output_dir=output_dir,
            target_number=target_number,
            frames_to_skip=frames_to_skip,
            on_candidate_found=_make_save_candidate_callback(job_id, target_number),
            should_stop=_make_check_stop_callback(job_id, stage_status),
            start_ts=start_ts,
            end_ts=end_ts,
        )

        from app.core.database import get_session
        session = next(get_session())
        try:
            job = session.get(ProcessingJob, job_id)
            if job and job.status == stage_status:
                job.status = "WAITING_USER"
                job.updated_at = datetime.now(timezone.utc)
                session.commit()
                print(f"[{stage_status}] Vídeo inteiro verificado. Aguardando usuário.")
        finally:
            session.close()

    except Exception as exc:
        print(f"[{stage_status} ERROR] Falha:")
        print(traceback.format_exc())
        _retry_or_fail(task_self, job_id, exc)


@celery_app.task(
    name="app.modules.clips.tasks.download_and_process_drive_video",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=3,
    default_retry_delay=5,
)
def download_and_process_drive_video(
    self,
    job_id: uuid.UUID,
    file_id: str,
    access_token: str,
    target_number: int,
    start_ts: int,
    end_ts: int,
):
    """Baixa o vídeo do Google Drive em streaming e dispara o Fast Scan."""
    from pathlib import Path
    from app.core.database import get_session
    from app.modules.clips.models import Video, ProcessingJob
    from app.modules.clips.google_drive import download_google_drive_file_streaming

    print(f"[GOOGLE DRIVE] Iniciando download do arquivo {file_id} para o job {job_id}")

    session = next(get_session())
    storage = get_storage()
    video_dest_path = None

    try:
        job = session.get(ProcessingJob, job_id)
        if not job:
            print(f"[GOOGLE DRIVE ERROR] Job {job_id} não encontrado no banco.")
            return

        if job.status != "DOWNLOADING" and not job.status.startswith("DOWNLOADING:"):
            print(f"[GOOGLE DRIVE] Ignorando download de job {job_id} no estado {job.status}.")
            return

        update_job_status(job_id, "DOWNLOADING")

        video = session.get(Video, job.video_id)
        if not video:
            print(f"[GOOGLE DRIVE ERROR] Vídeo do job {job_id} não encontrado.")
            update_job_status(job_id, "ERROR")
            return

        safe_name = Path(video.original_filename).name
        video_key = f"videos/{video.id}_{safe_name}"
        video_dest_path = storage.path_for(video_key)

        last_reported_pct = -1
        last_reported_time = 0.0

        def on_download_progress(downloaded: int, total: int):
            nonlocal last_reported_pct, last_reported_time
            now = time.time()
            pct = int((downloaded / total) * 100) if total > 0 else 0
            if (pct != last_reported_pct and (now - last_reported_time >= 1.5)) or pct in (50, 100):
                last_reported_pct = pct
                last_reported_time = now
                update_job_status(job_id, f"DOWNLOADING:{pct}")

        plain_token = decrypt_drive_token(access_token)

        # Download em streaming (chunks de 4MB) para não estourar RAM e acelerar transferência
        bytes_downloaded = download_google_drive_file_streaming(
            file_id=file_id,
            access_token=plain_token,
            destination_path=video_dest_path,
            on_progress=on_download_progress,
        )

        size_mb = bytes_downloaded / (1024 * 1024)
        video.storage_path = str(video_dest_path)
        video.file_size_mb = round(size_mb, 2)
        session.add(video)
        session.commit()
        print(f"[GOOGLE DRIVE] Download concluído com sucesso ({round(size_mb, 2)} MB). Disparando Fast Scan.")

        # Publica o Fast Scan para o pipeline de IA
        run_fast_scan.delay(job_id, str(video_dest_path), target_number, start_ts, end_ts)

    except Exception as exc:
        print(f"[GOOGLE DRIVE ERROR] Falha no download do vídeo do job {job_id}: {exc}")
        print(traceback.format_exc())
        if video_dest_path and Path(video_dest_path).exists():
            try:
                Path(video_dest_path).unlink(missing_ok=True)
            except Exception as rm_err:
                print(f"[GOOGLE DRIVE ERROR] Falha ao remover arquivo corrompido: {rm_err}")
        _retry_or_fail(self, job_id, exc)
    finally:
        session.close()


@celery_app.task(
    name="app.modules.clips.tasks.run_fast_scan",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=3,
    default_retry_delay=5,
)
def run_fast_scan(
    self,
    job_id: uuid.UUID,
    video_path: str,
    target_number: int,
    start_ts: int,
    end_ts: int,
):
    """FASE 1: busca expressa; salva candidatos no DB em tempo real."""
    _execute_scan_stage(
        task_self=self,
        job_id=job_id,
        video_path=video_path,
        target_number=target_number,
        start_ts=start_ts,
        end_ts=end_ts,
        stage_status="FAST_SCAN",
        allowed_initial_statuses=("PENDING", "CONVERTING", "FAST_SCAN"),
        frames_to_skip=30,
    )


@celery_app.task(
    name="app.modules.clips.tasks.run_deep_scan",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=3,
    default_retry_delay=5,
)
def run_deep_scan(
    self,
    job_id: uuid.UUID,
    video_path: str,
    target_number: int,
    start_ts: int,
    end_ts: int,
):
    """FASE 1B: busca aprofundada com amostragem mais densa de frames."""
    _execute_scan_stage(
        task_self=self,
        job_id=job_id,
        video_path=video_path,
        target_number=target_number,
        start_ts=start_ts,
        end_ts=end_ts,
        stage_status="DEEP_SCAN",
        allowed_initial_statuses=("FAST_SCAN", "WAITING_USER", "DEEP_SCAN", "CONVERTING"),
        frames_to_skip=10,
    )


@celery_app.task(
    name="app.modules.clips.tasks.run_full_tracking",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=3,
    default_retry_delay=5,
)
def run_full_tracking(
    self,
    job_id: uuid.UUID,
    video_path: str,
    target_number: int,
    target_signature: str,
    start_ts: int,
    end_ts: int,
):
    """FASE 2: rastreio rigoroso filtrando pela assinatura (número + cor)."""
    current_status = _get_job_status(job_id)
    if current_status is not None and current_status not in ("TRACKING", "EXTRACTING"):
        print(f"[TRACKING] Ignorando job {job_id} no estado {current_status}.")
        return

    print(f"[TRACKING] Iniciando recorte final do job {job_id}")
    update_job_status(job_id, "TRACKING")

    def save_clip_to_db(clip_dict):
        from app.core.database import get_session
        session = next(get_session())
        try:
            new_clip = Clip(
                job_id=job_id,
                storage_path=clip_dict["path"],
                start_timestamp=clip_dict["start_ts"],
                end_timestamp=clip_dict["end_ts"],
            )
            session.add(new_clip)
            job = session.get(ProcessingJob, job_id)
            if job:
                job.updated_at = datetime.now(timezone.utc)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"[db error] Falha ao salvar clipe: {e}")
        finally:
            session.close()

    def set_extracting_status():
        print("[TRACKING] Iniciando recorte de clipes. Mudando status para EXTRACTING.")
        update_job_status(job_id, "EXTRACTING")

    try:
        resolved_path = _resolve_video_path(job_id, video_path)
        _clear_partial_clips(job_id)

        from ml.scripts.process_video import _get_pipeline
        # Import lazy: psutil/pynvml só existem no worker, não na API
        from app.modules.clips.perf_monitor import PerformanceMonitor
        pipeline = _get_pipeline()
        output_dir = str(CLIPS_DIR / str(job_id))

        # Mede CPU/RAM do worker e uso da GPU durante a geração dos clipes
        with PerformanceMonitor("tracking", job_id, resolved_path, output_dir):
            pipeline.process(
                video_path=resolved_path,
                target_number=target_number,
                target_signature=target_signature,
                output_dir=output_dir,
                start_ts=start_ts,
                end_ts=end_ts,
                on_clip_generated=save_clip_to_db,
                on_extracting_start=set_extracting_status,
                debug=True,
            )

        update_job_status(job_id, "COMPLETED")
        print(f"[TRACKING] Job {job_id} concluído.")

    except Exception as exc:
        print("[TRACKING ERROR] Falha:")
        print(traceback.format_exc())
        _retry_or_fail(self, job_id, exc)


def _resolve_target_signature(session, job: ProcessingJob) -> str | None:
    """Busca a assinatura de candidato mais compatível para retomar o tracking."""
    from sqlmodel import select
    candidates = session.exec(
        select(Candidate).where(Candidate.job_id == job.id)
    ).all()
    for cand in candidates:
        if cand.number == job.target_number and cand.is_target:
            return cand.signature
    for cand in candidates:
        if cand.number == job.target_number:
            return cand.signature
    for cand in candidates:
        if cand.is_target:
            return cand.signature
    return None


def recover_interrupted_jobs() -> int:
    """Retoma jobs presos em estados intermediários quando o worker reinicia."""
    from app.core.database import get_session
    from app.modules.clips.models import Video
    from sqlmodel import select

    interrupted_statuses = (
        "PENDING",
        "CONVERTING",
        "FAST_SCAN",
        "DEEP_SCAN",
        "TRACKING",
        "EXTRACTING",
        "DOWNLOADING",
    )
    session = next(get_session())
    recovered = 0
    try:
        jobs = session.exec(
            select(ProcessingJob).where(
                ProcessingJob.status.in_(interrupted_statuses)
                | ProcessingJob.status.like("DOWNLOADING:%")
            )
        ).all()

        for job in jobs:
            video = session.get(Video, job.video_id)
            has_video_file = bool(
                video and video.storage_path and Path(video.storage_path).exists()
            )

            if job.status == "DOWNLOADING" or job.status.startswith("DOWNLOADING:"):
                if has_video_file:
                    run_fast_scan.delay(
                        job.id, video.storage_path, job.target_number, 0, 0
                    )
                    recovered += 1
                else:
                    job.status = "ERROR"
                    job.updated_at = datetime.now(timezone.utc)
                    session.add(job)
                continue

            if not has_video_file:
                job.status = "ERROR"
                job.updated_at = datetime.now(timezone.utc)
                session.add(job)
                continue

            if job.status in ("PENDING", "CONVERTING", "FAST_SCAN"):
                run_fast_scan.delay(
                    job.id, video.storage_path, job.target_number, 0, 0
                )
                recovered += 1
            elif job.status == "DEEP_SCAN":
                run_deep_scan.delay(
                    job.id, video.storage_path, job.target_number, 0, 0
                )
                recovered += 1
            elif job.status in ("TRACKING", "EXTRACTING"):
                target_sig = _resolve_target_signature(session, job)
                run_full_tracking.delay(
                    job.id,
                    video.storage_path,
                    job.target_number,
                    target_sig or "",
                    0,
                    0,
                )
                recovered += 1

        session.commit()
        if recovered:
            print(f"[WORKER RECOVERY] {recovered} job(s) retomado(s) após reinício.")
        return recovered
    except Exception as exc:
        session.rollback()
        print(f"[WORKER RECOVERY ERROR] Falha ao recuperar jobs interrompidos: {exc}")
        traceback.print_exc()
        return 0
    finally:
        session.close()


@worker_ready.connect
def _on_worker_ready(sender=None, **kwargs):
    recover_interrupted_jobs()


@celery_app.task(name="app.modules.clips.tasks.run_retention_policy")
def run_retention_policy():
    print("[RETENTION POLICY] Iniciando rotina de limpeza de armazenamento.")
    from app.core.database import get_session
    from sqlmodel import select
    from app.modules.clips.models import Video

    session = next(get_session())
    storage = get_storage()
    try:
        fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)

        # 1. Clipes TEMPORARY com mais de 14 dias
        clips_to_delete = session.exec(
            select(Clip).where(Clip.status == "TEMPORARY", Clip.created_at < fourteen_days_ago)
        ).all()

        for clip in clips_to_delete:
            print(f"[RETENTION POLICY] Deletando clipe {clip.id}")
            storage.delete(clip.storage_path)
            clip.storage_path = None
            clip.status = "DELETED"
            session.add(clip)

        # 2. Vídeos brutos com mais de 14 dias que não possuem jobs em andamento
        active_statuses = [
            "DOWNLOADING",
            "PENDING",
            "CONVERTING",
            "FAST_SCAN",
            "WAITING_USER",
            "DEEP_SCAN",
            "TRACKING",
            "EXTRACTING",
        ]
        videos = session.exec(
            select(Video).where(Video.uploaded_at < fourteen_days_ago, Video.storage_path != None)
        ).all()

        for video in videos:
            has_active_job = any(
                job.status in active_statuses or job.status.startswith("DOWNLOADING:")
                for job in video.jobs
            )
            if not has_active_job:
                print(f"[RETENTION POLICY] Deletando vídeo bruto {video.id}")
                storage.delete(video.storage_path)
                video.storage_path = None

                # Delete thumbnails for candidates of completed jobs for this video
                for job in video.jobs:
                    for candidate in job.candidates:
                        if candidate.image_path:
                            storage.delete(candidate.image_path)
                            candidate.image_path = None
                            session.add(candidate)

                session.add(video)

        session.commit()
        print("[RETENTION POLICY] Rotina finalizada com sucesso.")
    except Exception as e:
        session.rollback()
        print(f"[RETENTION POLICY ERROR] Falha na rotina: {e}")
        traceback.print_exc()
    finally:
        session.close()

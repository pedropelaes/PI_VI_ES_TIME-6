"""
Rotas para criação e consulta de jobs de processamento.
Fluxo: Upload vídeo → cria Video → cria ProcessingJob → roda ML em background.
"""
import asyncio
import uuid
import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

import httpx

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.core.config import MAX_VIDEO_SIZE_MB
from app.core.database import get_session, engine
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError, ForbiddenError, ConflictError, DomainError, UnauthorizedError, BadRequestError
from app.core.security import decode_access_token, encrypt_drive_token
from app.core.storage import get_storage
from app.modules.identity.models import User, UserRole
from app.modules.clips.models import Video, ProcessingJob, Clip, ClipStatus, Candidate
from app.modules.clips.schemas import (
    ConfirmPlayerRequest,
    GoogleDriveImportRequest,
    RefineSearchRequest,
)
from app.modules.clips.google_drive import get_google_drive_file_metadata
from app.modules.clips.tasks import (
    run_fast_scan,
    run_deep_scan,
    run_full_tracking,
    download_and_process_drive_video,
)
from app.modules.profiles.models import AthleteProfile

router = APIRouter(prefix="/jobs", tags=["jobs"])
videos_router = APIRouter(prefix="/videos", tags=["videos"])

BASE_DIR = Path(__file__).resolve().parents[2]

UPLOAD_DIR = BASE_DIR / "uploads" / "videos"
CLIPS_DIR  = BASE_DIR / "uploads" / "clips"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)


def _delete_job_and_orphan_video(session: Session, job: ProcessingJob) -> None:
    """
    Apaga o job (candidatos somem via cascade). Se nenhum outro job ainda
    apontar para o mesmo vídeo, apaga também o vídeo original (linha + arquivo).
    Assume que todos os clipes do job já foram apagados por quem chamou.
    """
    video_id = job.video_id
    session.delete(job)
    session.flush()

    other_job_using_video = session.exec(
        select(ProcessingJob).where(ProcessingJob.video_id == video_id)
    ).first()
    if other_job_using_video:
        return

    video = session.get(Video, video_id)
    if video:
        if video.storage_path:
            get_storage().delete(video.storage_path)
        session.delete(video)


def _get_stream_user(
    request: Request,
    token: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> User:
    """Autentica conexões SSE aceitando `?token=` (EventSource) ou `Authorization: Bearer`."""
    raw_token = token
    if not raw_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            raw_token = auth_header[7:].strip()

    if not raw_token:
        raise UnauthorizedError("Token inválido ou expirado.")

    user_id = decode_access_token(raw_token)
    if not user_id:
        raise UnauthorizedError("Token inválido ou expirado.")

    try:
        uid = uuid.UUID(user_id)
    except ValueError as exc:
        raise UnauthorizedError("Token inválido ou expirado.") from exc

    user = session.get(User, uid)
    if not user:
        raise UnauthorizedError("Token inválido ou expirado.")

    return user


def _get_owned_job(
    session: Session,
    job_id: uuid.UUID,
    current_user: User,
) -> tuple[ProcessingJob, Video]:
    """Busca um job e valida que pertence ao usuário autenticado."""
    job = session.get(ProcessingJob, job_id)
    if not job:
        raise NotFoundError("Job não encontrado.")

    video = session.get(Video, job.video_id)
    if not video or video.user_id != current_user.id:
        raise ForbiddenError("Este job não pertence ao usuário autenticado.")

    return job, video


@router.get("/{job_id}/stream")
def stream_job_status(
    job_id: uuid.UUID,
    current_user: User = Depends(_get_stream_user),
    session: Session = Depends(get_session),
):
    job = session.get(ProcessingJob, job_id)
    if job:
        video = session.get(Video, job.video_id)
        if not video or video.user_id != current_user.id:
            raise ForbiddenError("Este job não pertence ao usuário autenticado.")

    def event_generator():
        while True:
            with Session(engine) as session:
                job = session.get(ProcessingJob, job_id)
                if not job:
                    yield f"data: {json.dumps({'error': 'Job não encontrado'})}\n\n"
                    return

                status_val = job.status
                download_progress = None
                if status_val.startswith("DOWNLOADING:"):
                    try:
                        download_progress = int(status_val.split(":")[1])
                        status_val = "DOWNLOADING"
                    except Exception:
                        pass

                clips = session.exec(select(Clip).where(Clip.job_id == job_id)).all()
                candidatos = session.exec(select(Candidate).where(Candidate.job_id == job_id)).all()

                payload = {
                    "job_id": str(job.id),
                    "status": status_val,
                    "download_progress": download_progress,
                    "candidates": [
                        {
                            "id": c.signature,
                            "name": c.name,
                            "number": c.number,
                            "color_hex": c.color_hex,
                            "image": c.image_path,
                            "is_target": c.is_target
                        }
                        for c in candidatos
                    ],
                    "clips": [
                        {
                            "id": str(c.id),
                            "file_url": f"/uploads/clips/{job_id}/{Path(c.storage_path).name}" if c.storage_path else None,
                            "start_timestamp": c.start_timestamp,
                            "end_timestamp": c.end_timestamp,
                            "duration": round(c.end_timestamp - c.start_timestamp, 2),
                            "status": c.status,
                            "published_at": c.published_at.isoformat() if c.published_at else None,
                        }
                        for c in clips
                    ]
                }

                done = status_val in ["COMPLETED", "ERROR"]

            yield f"data: {json.dumps(payload)}\n\n"

            if done:
                return

            time.sleep(2.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/", status_code=202)
async def create_job(
    target_number: int  = Form(..., ge=0, le=999),
    video: UploadFile   = File(...),
    start_ts: int       = Form(0),
    end_ts: int         = Form(0),
    current_user: User  = Depends(get_current_user),
    session: Session    = Depends(get_session),
):
    """Fase 1: Recebe vídeo em chunks de 4 MB no disco e dispara o Fast Scan."""
    # 1. Salva o arquivo em disco por partes (sem carregar tudo na RAM)
    video_id   = uuid.uuid4()
    safe_name  = Path(str(video.filename or "video.mp4")).name or "video.mp4"

    storage = get_storage()
    max_bytes = MAX_VIDEO_SIZE_MB * 1024 * 1024
    await video.seek(0)
    try:
        video_path, total_bytes = await asyncio.to_thread(
            storage.save_stream,
            video.file,
            f"videos/{video_id}_{safe_name}",
            4 * 1024 * 1024,
            max_bytes,
        )
    except ValueError as exc:
        raise BadRequestError(
            f"O arquivo excede o limite máximo permitido de {MAX_VIDEO_SIZE_MB}MB."
        ) from exc

    size_mb = total_bytes / (1024 * 1024)

    # 2. Cria registro Video
    db_video = Video(
        id                = video_id,
        user_id           = current_user.id,
        original_filename = safe_name,
        storage_path      = str(video_path),
        file_size_mb      = round(size_mb, 2),
    )
    session.add(db_video)
    session.commit()
    session.refresh(db_video)

    # 3. Cria ProcessingJob
    job = ProcessingJob(
        video_id      = video_id,
        target_number = target_number,
        status        = "PENDING",
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    # 4. Publica o FAST SCAN (fase 1) na fila do worker
    run_fast_scan.delay(job.id, str(video_path), target_number, start_ts, end_ts)

    return {"job_id": str(job.id), "status": job.status}


@router.post("/import/google-drive", status_code=202)
@videos_router.post("/import/google-drive", status_code=202)
async def import_video_from_google_drive(
    payload: GoogleDriveImportRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Importa vídeo do Google Drive:
    1. Valida formato e tamanho na Drive API v3 (rejeita 401, 403, 400 imediatamente).
    2. Cria registro Video e ProcessingJob (status DOWNLOADING).
    3. Despacha download assíncrono em chunks para o worker Celery.
    """
    metadata = await get_google_drive_file_metadata(
        file_id=payload.file_id,
        access_token=payload.google_access_token,
    )

    safe_name = Path(str(metadata["name"])).name
    video_id = uuid.uuid4()
    size_mb = metadata.get("size", 0) / (1024 * 1024)

    db_video = Video(
        id=video_id,
        user_id=current_user.id,
        original_filename=safe_name,
        storage_path=None,
        file_size_mb=round(size_mb, 2) if size_mb > 0 else None,
    )
    session.add(db_video)
    session.commit()
    session.refresh(db_video)

    job = ProcessingJob(
        video_id=video_id,
        target_number=payload.target_number,
        status="DOWNLOADING",
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    download_and_process_drive_video.delay(
        job.id,
        payload.file_id,
        encrypt_drive_token(payload.google_access_token),
        payload.target_number,
        payload.start_ts,
        payload.end_ts,
    )

    return {"job_id": str(job.id), "status": job.status}


@router.get("/drive-preview/{file_id}")
@videos_router.get("/drive-preview/{file_id}")
async def preview_drive_video(
    file_id: str,
    access_token: str = Query(...),
    request: Request = None,
):
    """
    Proxy de streaming com suporte a HTTP Range (206 Partial Content) para permitir
    que o player HTML5 <video> reproduza vídeos do Google Drive e descubra a duração
    para o Slider de recorte sem precisar baixar o arquivo inteiro com antecedência.
    """
    range_header = request.headers.get("range") if request else None
    google_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    headers = {"Authorization": f"Bearer {access_token}"}
    if range_header:
        headers["Range"] = range_header

    client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)
    try:
        req = client.build_request("GET", google_url, headers=headers)
        res = await client.send(req, stream=True)
    except Exception as exc:
        await client.aclose()
        raise BadRequestError(f"Falha ao conectar ao Google Drive para preview: {exc}")

    if res.status_code not in (200, 206):
        await res.aclose()
        await client.aclose()
        if res.status_code == 401:
            raise UnauthorizedError("Token do Google Drive expirado.")
        if res.status_code == 403:
            raise ForbiddenError("Sem permissão para visualizar este vídeo do Google Drive.")
        if res.status_code == 404:
            raise NotFoundError("Vídeo não encontrado no Google Drive.")
        raise BadRequestError(f"Erro ao transmitir vídeo do Google Drive (status {res.status_code}).")

    async def stream_generator():
        try:
            async for chunk in res.aiter_bytes(chunk_size=128 * 1024):
                yield chunk
        finally:
            await res.aclose()
            await client.aclose()

    resp_headers = {
        "Accept-Ranges": "bytes",
    }
    for key in ("Content-Range", "Content-Length", "Content-Type"):
        val = res.headers.get(key)
        if val:
            resp_headers[key] = val

    return StreamingResponse(
        stream_generator(),
        status_code=res.status_code,
        headers=resp_headers,
        media_type=res.headers.get("Content-Type", "video/mp4"),
    )

@router.delete("/{job_id}/clips", status_code=204)
def delete_job_clips(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Apaga todos os clipes de um job (remove o job do histórico)."""
    job, _ = _get_owned_job(session, job_id, current_user)

    storage = get_storage()
    clips = session.exec(select(Clip).where(Clip.job_id == job_id)).all()
    for clip in clips:
        if clip.storage_path:
            storage.delete(clip.storage_path)
        session.delete(clip)
    session.flush()

    _delete_job_and_orphan_video(session, job)
    session.commit()


@router.post("/{job_id}/confirm")
def confirm_player(
    job_id: uuid.UUID,
    payload: ConfirmPlayerRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    job, video = _get_owned_job(session, job_id, current_user)

    if job.status not in ["FAST_SCAN", "WAITING_USER", "DEEP_SCAN"]:
        raise ConflictError("Este job não aceita mais confirmações.")

    if not video.storage_path:
        raise DomainError("Erro interno: Vídeo não atrelado ao Job.")

    if "_" in payload.candidate_signature:
        try:
            novo_numero = int(payload.candidate_signature.split("_")[0])
            job.target_number = novo_numero
        except ValueError:
            pass

    job.status = "TRACKING"
    job.updated_at = datetime.now(timezone.utc)
    session.add(job)
    session.commit()

    run_full_tracking.delay(
        job.id,
        video.storage_path,
        job.target_number,
        payload.candidate_signature,
        payload.start_ts,
        payload.end_ts,
    )

    return {"message": "Processamento retomado.", "status": "TRACKING"}


@router.post("/{job_id}/refine")
def refine_search(
    job_id: uuid.UUID,
    payload: RefineSearchRequest | None = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Dispara uma busca aprofundada (DEEP_SCAN) para localizar o jogador-alvo."""
    job, video = _get_owned_job(session, job_id, current_user)

    if job.status not in ["FAST_SCAN", "WAITING_USER"]:
        raise ConflictError("Este job não aceita refinamento de busca no momento.")

    if not video.storage_path:
        raise DomainError("Erro interno: Vídeo não atrelado ao Job.")

    start_ts = payload.start_ts if payload else 0
    end_ts = payload.end_ts if payload else 0

    job.status = "DEEP_SCAN"
    job.updated_at = datetime.now(timezone.utc)
    session.add(job)
    session.commit()

    run_deep_scan.delay(
        job.id,
        video.storage_path,
        job.target_number,
        start_ts,
        end_ts,
    )

    return {"message": "Busca aprofundada iniciada.", "status": "DEEP_SCAN"}

clips_router = APIRouter(prefix="/clips", tags=["clips"])
brasilia = timezone(timedelta(hours=-3))


@clips_router.get("/")
def list_clips(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    jobs = session.exec(
        select(ProcessingJob)
        .join(Video, ProcessingJob.video_id == Video.id)
        .where(Video.user_id == current_user.id)
        .where(ProcessingJob.status == "COMPLETED")
        .order_by(ProcessingJob.created_at.desc())
    ).all()

    result = []
    for job in jobs:
        clips = session.exec(select(Clip).where(Clip.job_id == job.id)).all()
        if not clips:
            continue
        result.append({
            "job_id": str(job.id),
            "target_number": job.target_number,
            "generated_at": job.updated_at.astimezone(brasilia).strftime("%d/%m/%Y - %H:%M"),
            "clips": [
                {
                    "id": str(c.id),
                    "file_url": f"/uploads/clips/{job.id}/{Path(c.storage_path).name}" if c.storage_path else None,
                    "duration": _format_duration(c.end_timestamp - c.start_timestamp),
                    "status": c.status,
                    "published_at": c.published_at,
                }
                for c in clips
            ],
        })
    return result


@clips_router.delete("/{clip_id}", status_code=204)
def delete_clip(
    clip_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    clip = session.get(Clip, clip_id)
    if not clip:
        raise NotFoundError("Clipe não encontrado.")

    job = session.get(ProcessingJob, clip.job_id)
    video = session.get(Video, job.video_id) if job else None
    if not video or video.user_id != current_user.id:
        raise ForbiddenError("Este clipe não pertence ao usuário autenticado.")

    if clip.storage_path:
        get_storage().delete(clip.storage_path)
    session.delete(clip)
    session.flush()

    remaining_clip = session.exec(select(Clip).where(Clip.job_id == job.id)).first()
    if not remaining_clip:
        _delete_job_and_orphan_video(session, job)

    session.commit()

def _get_owned_clip(session: Session, clip_id: uuid.UUID, user: User) -> Clip:
    clip = session.get(Clip, clip_id)
    if not clip:
        raise NotFoundError("Clipe não encontrado.")
    job = session.get(ProcessingJob, clip.job_id)
    video = session.get(Video, job.video_id) if job else None
    if not video or video.user_id != user.id:
        raise ForbiddenError("Este clipe não pertence ao usuário autenticado.")
    return clip


def _publication_state(clip: Clip) -> dict:
    return {"id": str(clip.id), "status": clip.status, "published_at": clip.published_at}


@clips_router.post("/{clip_id}/publish")
def publish_clip(
    clip_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Publica no feed. Publicado, sai da retenção de 14 dias. Idempotente."""
    if current_user.role != UserRole.ATHLETE:
        raise ForbiddenError("Apenas atletas podem publicar clipes no feed.")

        # O feed junta o clipe ao perfil do atleta (INNER JOIN): sem perfil, o clipe nao apareceria.
    perfil = session.exec(
        select(AthleteProfile).where(AthleteProfile.user_id == current_user.id)
    ).first()
    if perfil is None:
        raise ConflictError("Complete seu perfil de atleta antes de publicar no feed.")

    clip = _get_owned_clip(session, clip_id, current_user)
    if clip.status == ClipStatus.DELETED or not clip.storage_path:
        raise ConflictError("Este clipe expirou e não pode mais ser publicado.")

    if clip.status != ClipStatus.PUBLISHED:
        clip.status = ClipStatus.PUBLISHED
        clip.published_at = datetime.now(timezone.utc)
        session.add(clip)
        session.commit()
        session.refresh(clip)

    return _publication_state(clip)


@clips_router.delete("/{clip_id}/publish")
def unpublish_clip(
    clip_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Tira o clipe do feed e o devolve a TEMPORARY. A retencao de 14 dias passa a contar
    a partir da despublicacao (created_at e reiniciado), e nao da geracao original.
    """
    clip = _get_owned_clip(session, clip_id, current_user)

    if clip.status == ClipStatus.PUBLISHED:
        clip.status = ClipStatus.TEMPORARY
        clip.published_at = None
        clip.created_at = datetime.now(timezone.utc)
        session.add(clip)
        session.commit()
        session.refresh(clip)

    return _publication_state(clip)
@clips_router.get("/athletes/{user_id}")
def list_athlete_clips(
    user_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Clipes de um atleta especifico, para a videoteca do perfil publico.

    Um `user_id` inexistente ou de usuario que nao e ATHLETE gera 404 (NotFoundError):
    nao existe atleta com aquele id, e a distincao nao interessa ao cliente (secao 5.5
    da spec). Ja um atleta que existe mas ainda nao tem clipes devolve lista vazia com
    200 -- sao situacoes diferentes.
    """
    target = session.get(User, user_id)
    if target is None or target.role != UserRole.ATHLETE:
        raise NotFoundError("Atleta não encontrado.")

    clips = session.exec(
        select(Clip)
        .join(ProcessingJob, Clip.job_id == ProcessingJob.id)
        .join(Video, ProcessingJob.video_id == Video.id)
        .where(Video.user_id == user_id)
        .where(ProcessingJob.status == "COMPLETED")
        .where(Clip.status != "DELETED")
        .where(Clip.storage_path.is_not(None))
        .order_by(Clip.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return [
        {
            "id": str(c.id),
            "duration_seconds": round(c.end_timestamp - c.start_timestamp, 2),
            "file_url": f"/uploads/clips/{c.job_id}/{Path(c.storage_path).name}",
            "created_at": c.created_at,
        }
        for c in clips
    ]



def _format_duration(seconds: float) -> str:
    total = int(seconds)
    m = total // 60
    s = total % 60
    return f"{m}:{s:02d}"

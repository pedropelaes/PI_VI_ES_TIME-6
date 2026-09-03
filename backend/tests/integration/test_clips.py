"""
Tests for clip endpoints:
  GET    /api/v1/clips/
  DELETE /api/v1/clips/{clip_id}
  DELETE /api/v1/jobs/{job_id}/clips
"""
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.identity.models import User
from app.modules.clips.models import Video, ProcessingJob, Clip, Candidate
from app.core.security import hash_password
from app.core.storage import get_storage

from .test_jobs import register_and_get_token, auth_headers


def _create_completed_job_with_clip(session: Session, owner_email: str) -> tuple[User, ProcessingJob, Clip]:
    user = User(
        email=owner_email,
        password_hash=hash_password("password123"),
        first_name="Owner",
        last_name="User",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    video = Video(
        user_id=user.id,
        original_filename="test.mp4",
        storage_path=str(get_storage().path_for(f"videos/{uuid.uuid4()}_test.mp4")),
        file_size_mb=1.0,
    )
    session.add(video)
    session.commit()
    session.refresh(video)

    job = ProcessingJob(video_id=video.id, target_number=10, status="COMPLETED")
    session.add(job)
    session.commit()
    session.refresh(job)

    clip = Clip(
        job_id=job.id,
        storage_path=str(get_storage().path_for(f"clips/{job.id}/clip.mp4")),
        start_timestamp=0.0,
        end_timestamp=5.0,
    )
    session.add(clip)
    session.commit()
    session.refresh(clip)

    return user, job, clip


def _create_completed_job_with_clips(session: Session, owner_email: str, n: int) -> tuple[User, ProcessingJob, list[Clip]]:
    user, job, first_clip = _create_completed_job_with_clip(session, owner_email)
    clips = [first_clip]
    for _ in range(n - 1):
        clip = Clip(
            job_id=job.id,
            storage_path=str(get_storage().path_for(f"clips/{job.id}/{uuid.uuid4()}.mp4")),
            start_timestamp=0.0,
            end_timestamp=5.0,
        )
        session.add(clip)
        session.commit()
        session.refresh(clip)
        clips.append(clip)
    return user, job, clips


def test_delete_clip_not_found(client: TestClient):
    token = register_and_get_token(client, email="deleteclip_nf@example.com")
    resp = client.delete(f"/api/v1/clips/{uuid.uuid4()}", headers=auth_headers(token))
    assert resp.status_code == 404


def test_delete_clip_unauthenticated(client: TestClient, session: Session):
    _, _, clip = _create_completed_job_with_clip(session, "deleteclip_owner1@example.com")
    resp = client.delete(f"/api/v1/clips/{clip.id}")
    assert resp.status_code in (401, 403)


def test_delete_clip_forbidden_when_not_owner(client: TestClient, session: Session):
    _, _, clip = _create_completed_job_with_clip(session, "deleteclip_owner2@example.com")
    other_token = register_and_get_token(client, email="deleteclip_intruder@example.com")

    resp = client.delete(f"/api/v1/clips/{clip.id}", headers=auth_headers(other_token))

    assert resp.status_code == 403
    assert session.get(Clip, clip.id) is not None


def test_delete_clip_success_removes_row_and_file(client: TestClient, session: Session):
    user, _, clip = _create_completed_job_with_clip(session, "deleteclip_owner3@example.com")
    Path(clip.storage_path).parent.mkdir(parents=True, exist_ok=True)
    Path(clip.storage_path).write_bytes(b"fake mp4 bytes")
    # Capturados antes do expire_all: depois dele, ler um atributo do objeto cuja linha
    # sumiu (em vez de um id/str plano) dispara ObjectDeletedError ao tentar recarregar.
    clip_id = clip.id
    clip_storage_path = clip.storage_path

    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    token = login.json()["access_token"]

    resp = client.delete(f"/api/v1/clips/{clip_id}", headers=auth_headers(token))

    assert resp.status_code == 204
    # O request rodou numa Session diferente da do teste; sem isso, session.get devolve o
    # objeto que ja estava no identity map em vez de consultar o banco de novo.
    session.expire_all()
    assert session.get(Clip, clip_id) is None
    assert not Path(clip_storage_path).exists()


def test_delete_clip_empties_job_from_history_list(client: TestClient, session: Session):
    user, job, clip = _create_completed_job_with_clip(session, "deleteclip_owner4@example.com")

    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    token = login.json()["access_token"]

    before = client.get("/api/v1/clips/", headers=auth_headers(token)).json()
    assert any(g["job_id"] == str(job.id) for g in before)

    client.delete(f"/api/v1/clips/{clip.id}", headers=auth_headers(token))

    after = client.get("/api/v1/clips/", headers=auth_headers(token)).json()
    assert all(g["job_id"] != str(job.id) for g in after)


def test_delete_clip_last_clip_also_deletes_job_and_video(client: TestClient, session: Session):
    """Apagar o último clipe de um job também apaga o job e o vídeo original (sem outro job usando)."""
    user, job, clip = _create_completed_job_with_clip(session, "deleteclip_owner5@example.com")
    job_id = job.id
    clip_id = clip.id
    video_id = job.video_id
    video_path = session.get(Video, video_id).storage_path
    Path(video_path).parent.mkdir(parents=True, exist_ok=True)
    Path(video_path).write_bytes(b"fake video bytes")

    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    token = login.json()["access_token"]

    resp = client.delete(f"/api/v1/clips/{clip_id}", headers=auth_headers(token))

    assert resp.status_code == 204
    # Idem: forca releitura do banco em vez do identity map desatualizado do teste.
    session.expire_all()
    assert session.get(ProcessingJob, job_id) is None
    assert session.get(Video, video_id) is None
    assert not Path(video_path).exists()


def test_delete_clip_not_last_clip_keeps_job_and_video(client: TestClient, session: Session):
    """Apagar um clipe que não é o último não deve apagar job nem vídeo."""
    user, job, clips = _create_completed_job_with_clips(session, "deleteclip_owner6@example.com", n=2)

    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    token = login.json()["access_token"]

    resp = client.delete(f"/api/v1/clips/{clips[0].id}", headers=auth_headers(token))

    assert resp.status_code == 204
    assert session.get(ProcessingJob, job.id) is not None
    assert session.get(Video, job.video_id) is not None


# ---------------------------------------------------------------------------
# DELETE /api/v1/jobs/{job_id}/clips — delete_job_clips
# ---------------------------------------------------------------------------

def test_delete_job_clips_job_not_found(client: TestClient):
    token = register_and_get_token(client, email="deletejob_nf@example.com")
    resp = client.delete(f"/api/v1/jobs/{uuid.uuid4()}/clips", headers=auth_headers(token))
    assert resp.status_code == 404


def test_delete_job_clips_unauthenticated(client: TestClient, session: Session):
    _, job, _ = _create_completed_job_with_clips(session, "deletejob_owner1@example.com", n=2)
    resp = client.delete(f"/api/v1/jobs/{job.id}/clips")
    assert resp.status_code in (401, 403)


def test_delete_job_clips_forbidden_when_not_owner(client: TestClient, session: Session):
    _, job, clips = _create_completed_job_with_clips(session, "deletejob_owner2@example.com", n=2)
    other_token = register_and_get_token(client, email="deletejob_intruder@example.com")

    resp = client.delete(f"/api/v1/jobs/{job.id}/clips", headers=auth_headers(other_token))

    assert resp.status_code == 403
    for clip in clips:
        assert session.get(Clip, clip.id) is not None


def test_delete_job_clips_success_removes_all_rows_and_files(client: TestClient, session: Session):
    user, job, clips = _create_completed_job_with_clips(session, "deletejob_owner3@example.com", n=3)
    for clip in clips:
        Path(clip.storage_path).parent.mkdir(parents=True, exist_ok=True)
        Path(clip.storage_path).write_bytes(b"fake mp4 bytes")
    # Capturados antes do expire_all: os objetos `clip` tem a linha apagada pelo request, e
    # ler um atributo deles depois do expire dispara ObjectDeletedError ao tentar recarregar.
    clip_ids_and_paths = [(clip.id, clip.storage_path) for clip in clips]

    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    token = login.json()["access_token"]

    resp = client.delete(f"/api/v1/jobs/{job.id}/clips", headers=auth_headers(token))

    assert resp.status_code == 204
    session.expire_all()
    for clip_id, clip_storage_path in clip_ids_and_paths:
        assert session.get(Clip, clip_id) is None
        assert not Path(clip_storage_path).exists()


def test_delete_job_clips_removes_job_from_history_list(client: TestClient, session: Session):
    user, job, _ = _create_completed_job_with_clips(session, "deletejob_owner4_history@example.com", n=2)

    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    token = login.json()["access_token"]

    before = client.get("/api/v1/clips/", headers=auth_headers(token)).json()
    assert any(g["job_id"] == str(job.id) for g in before)

    resp = client.delete(f"/api/v1/jobs/{job.id}/clips", headers=auth_headers(token))
    assert resp.status_code == 204

    after = client.get("/api/v1/clips/", headers=auth_headers(token)).json()
    assert all(g["job_id"] != str(job.id) for g in after)


def test_delete_job_clips_also_deletes_job_and_video(client: TestClient, session: Session):
    user, job, clips = _create_completed_job_with_clips(session, "deletejob_owner5@example.com", n=2)
    job_id = job.id
    video_id = job.video_id
    video_path = session.get(Video, video_id).storage_path
    Path(video_path).parent.mkdir(parents=True, exist_ok=True)
    Path(video_path).write_bytes(b"fake video bytes")

    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    token = login.json()["access_token"]

    resp = client.delete(f"/api/v1/jobs/{job_id}/clips", headers=auth_headers(token))

    assert resp.status_code == 204
    session.expire_all()
    assert session.get(ProcessingJob, job_id) is None
    assert session.get(Video, video_id) is None
    assert not Path(video_path).exists()


def test_delete_job_clips_keeps_video_when_shared_by_another_job(client: TestClient, session: Session):
    """Se outro job ainda usa o mesmo vídeo, apagar um job não deve apagar o vídeo nem o outro job."""
    user, job1, _ = _create_completed_job_with_clips(session, "deletejob_owner6@example.com", n=1)

    job2 = ProcessingJob(video_id=job1.video_id, target_number=7, status="COMPLETED")
    session.add(job2)
    session.commit()
    session.refresh(job2)
    other_clip = Clip(
        job_id=job2.id,
        storage_path=str(get_storage().path_for(f"clips/{job2.id}/other.mp4")),
        start_timestamp=0.0,
        end_timestamp=3.0,
    )
    session.add(other_clip)
    session.commit()
    # Capturados antes do expire_all: job1 tem a linha apagada pelo request, e ler um
    # atributo dele depois do expire dispara ObjectDeletedError ao tentar recarregar.
    job1_id = job1.id
    job1_video_id = job1.video_id
    job2_id = job2.id
    other_clip_id = other_clip.id

    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    token = login.json()["access_token"]

    resp = client.delete(f"/api/v1/jobs/{job1_id}/clips", headers=auth_headers(token))

    assert resp.status_code == 204
    session.expire_all()
    assert session.get(ProcessingJob, job1_id) is None
    assert session.get(ProcessingJob, job2_id) is not None
    assert session.get(Video, job1_video_id) is not None
    assert session.get(Clip, other_clip_id) is not None


def test_delete_job_clips_cascades_candidates(client: TestClient, session: Session):
    user, job, _ = _create_completed_job_with_clips(session, "deletejob_owner7@example.com", n=1)
    candidate = Candidate(
        job_id=job.id,
        signature="10_#ff0000",
        name="Jogador Teste",
        number=10,
        image_path="fake.jpg",
        is_target=True,
    )
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    # Capturado antes do expire_all: ler candidate.id depois do expire dispara
    # ObjectDeletedError ao tentar recarregar a linha ja apagada pelo request.
    candidate_id = candidate.id
    job_id = job.id

    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    token = login.json()["access_token"]

    resp = client.delete(f"/api/v1/jobs/{job_id}/clips", headers=auth_headers(token))

    assert resp.status_code == 204
    session.expire_all()
    assert session.get(Candidate, candidate_id) is None

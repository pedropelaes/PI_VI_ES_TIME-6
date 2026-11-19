"""
Tests for job endpoints:
  POST /api/v1/jobs/
  GET  /api/v1/jobs/{id}/stream
  POST /api/v1/jobs/{id}/confirm
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.identity.models import User
from app.modules.clips.models import Video, ProcessingJob, Candidate
from app.core.security import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def register_and_get_token(client: TestClient, email: str = "job_test@example.com", password: str = "securepass123") -> str:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Job",
            "last_name": "Tester",
        },
    )
    assert resp.status_code == 200, f"Registration failed: {resp.text}"
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_user_video_job(session: Session, status: str = "WAITING_USER") -> tuple[User, Video, ProcessingJob]:
    """Directly create User + Video + ProcessingJob in the test DB."""
    user = User(
        email=f"jobowner_{uuid.uuid4().hex[:8]}@example.com",
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
        storage_path="/tmp/test.mp4",
        file_size_mb=1.0,
    )
    session.add(video)
    session.commit()
    session.refresh(video)

    job = ProcessingJob(
        video_id=video.id,
        target_number=10,
        status=status,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    return user, video, job


# ---------------------------------------------------------------------------
# POST /api/v1/jobs/ — create_job
# ---------------------------------------------------------------------------

def test_create_job_unauthenticated(client: TestClient):
    """Uploading without a token must be rejected."""
    resp = client.post(
        "/api/v1/jobs/",
        data={"target_number": "10", "start_ts": "0", "end_ts": "0"},
        files={"video": ("test.mp4", b"fake video bytes", "video/mp4")},
    )
    assert resp.status_code in (401, 403)


def test_create_job_success(client: TestClient):
    """Valid upload + auth token returns 202 with job_id and PENDING status."""
    token = register_and_get_token(client, email="createjob@example.com")

    with patch("app.modules.clips.router.run_fast_scan") as mock_task:
        response = client.post(
            "/api/v1/jobs/",
            data={"target_number": "10", "start_ts": "0", "end_ts": "0"},
            files={"video": ("test.mp4", b"fake video bytes", "video/mp4")},
            headers=auth_headers(token),
        )

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "PENDING"
    mock_task.delay.assert_called_once()


def test_create_job_invalid_number_negative(client: TestClient):
    """target_number < 0 must fail with 422 (Pydantic/FastAPI validation)."""
    token = register_and_get_token(client, email="negnum@example.com")

    with patch("app.modules.clips.router.run_fast_scan"):
        response = client.post(
            "/api/v1/jobs/",
            data={"target_number": "-1", "start_ts": "0", "end_ts": "0"},
            files={"video": ("test.mp4", b"fake video bytes", "video/mp4")},
            headers=auth_headers(token),
        )

    assert response.status_code == 422


def test_create_job_invalid_number_too_large(client: TestClient):
    """target_number > 999 must fail with 422 (Pydantic/FastAPI validation)."""
    token = register_and_get_token(client, email="bignum@example.com")

    with patch("app.modules.clips.router.run_fast_scan"):
        response = client.post(
            "/api/v1/jobs/",
            data={"target_number": "1000", "start_ts": "0", "end_ts": "0"},
            files={"video": ("test.mp4", b"fake video bytes", "video/mp4")},
            headers=auth_headers(token),
        )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/jobs/{id}/confirm — confirm_player
# ---------------------------------------------------------------------------

def test_confirm_player_unauthenticated(client: TestClient, session: Session):
    """Unauthenticated confirmation request must be rejected."""
    _, _, job = _create_user_video_job(session, status="WAITING_USER")
    resp = client.post(
        f"/api/v1/jobs/{job.id}/confirm",
        json={"candidate_signature": "10_#ff0000", "start_ts": 0, "end_ts": 0},
    )
    assert resp.status_code in (401, 403)


def test_confirm_player_forbidden_when_not_owner(client: TestClient, session: Session):
    """Confirming a job owned by another user must return 403."""
    _, _, job = _create_user_video_job(session, status="WAITING_USER")
    other_token = register_and_get_token(client, email="confirm_intruder@example.com")

    resp = client.post(
        f"/api/v1/jobs/{job.id}/confirm",
        json={"candidate_signature": "10_#ff0000", "start_ts": 0, "end_ts": 0},
        headers=auth_headers(other_token),
    )
    assert resp.status_code == 403


def test_confirm_player_job_not_found(client: TestClient):
    """Non-existent job UUID must return 404."""
    token = register_and_get_token(client, email="confirm_nf@example.com")
    random_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/jobs/{random_id}/confirm",
        json={"candidate_signature": "10_#ff0000", "start_ts": 0, "end_ts": 0},
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


def test_confirm_player_wrong_status(client: TestClient, session: Session):
    """Job in COMPLETED status must return 409 (no more confirmations accepted)."""
    user, _, job = _create_user_video_job(session, status="COMPLETED")
    token = create_access_token(str(user.id))

    with patch("app.modules.clips.router.run_full_tracking"):
        resp = client.post(
            f"/api/v1/jobs/{job.id}/confirm",
            json={"candidate_signature": "10_#ff0000", "start_ts": 0, "end_ts": 0},
            headers=auth_headers(token),
        )

    # F0 §10.2: estado não-confirmável agora é 409 Conflict (era 400)
    assert resp.status_code == 409


def test_confirm_player_success(client: TestClient, session: Session):
    """Job in WAITING_USER status with a valid signature returns 200 and status TRACKING."""
    user, _, job = _create_user_video_job(session, status="WAITING_USER")
    token = create_access_token(str(user.id))

    with patch("app.modules.clips.router.run_full_tracking") as mock_task:
        resp = client.post(
            f"/api/v1/jobs/{job.id}/confirm",
            json={"candidate_signature": "10_#ff0000", "start_ts": 0, "end_ts": 0},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "TRACKING"
    mock_task.delay.assert_called_once()

    # Verify the DB record was updated
    session.refresh(job)
    assert job.status == "TRACKING"


def test_confirm_player_fast_scan_status(client: TestClient, session: Session):
    """Job in FAST_SCAN status (user clicked early) also accepts confirmation."""
    user, _, job = _create_user_video_job(session, status="FAST_SCAN")
    token = create_access_token(str(user.id))

    with patch("app.modules.clips.router.run_full_tracking") as mock_task:
        resp = client.post(
            f"/api/v1/jobs/{job.id}/confirm",
            json={"candidate_signature": "10_#ff0000", "start_ts": 0, "end_ts": 0},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "TRACKING"
    mock_task.delay.assert_called_once()


def test_confirm_player_deep_scan_status(client: TestClient, session: Session):
    """Job in DEEP_SCAN status also accepts confirmation."""
    user, _, job = _create_user_video_job(session, status="DEEP_SCAN")
    token = create_access_token(str(user.id))

    with patch("app.modules.clips.router.run_full_tracking") as mock_task:
        resp = client.post(
            f"/api/v1/jobs/{job.id}/confirm",
            json={"candidate_signature": "10_#ff0000", "start_ts": 0, "end_ts": 0},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "TRACKING"
    mock_task.delay.assert_called_once()


# ---------------------------------------------------------------------------
# POST /api/v1/jobs/{id}/refine — refine_search (DEEP_SCAN)
# ---------------------------------------------------------------------------

def test_refine_search_success(client: TestClient, session: Session):
    """Refining a WAITING_USER job sets DEEP_SCAN and dispatches run_deep_scan."""
    user, _, job = _create_user_video_job(session, status="WAITING_USER")
    token = create_access_token(str(user.id))

    with patch("app.modules.clips.router.run_deep_scan") as mock_task:
        resp = client.post(
            f"/api/v1/jobs/{job.id}/refine",
            json={"start_ts": 5, "end_ts": 30},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "DEEP_SCAN"
    mock_task.delay.assert_called_once_with(job.id, "/tmp/test.mp4", 10, 5, 30)

    session.refresh(job)
    assert job.status == "DEEP_SCAN"


def test_refine_search_forbidden_when_not_owner(client: TestClient, session: Session):
    _, _, job = _create_user_video_job(session, status="WAITING_USER")
    other_token = register_and_get_token(client, email="refine_intruder@example.com")

    resp = client.post(
        f"/api/v1/jobs/{job.id}/refine",
        json={"start_ts": 0, "end_ts": 0},
        headers=auth_headers(other_token),
    )
    assert resp.status_code == 403


def test_refine_search_wrong_status(client: TestClient, session: Session):
    user, _, job = _create_user_video_job(session, status="COMPLETED")
    token = create_access_token(str(user.id))

    resp = client.post(
        f"/api/v1/jobs/{job.id}/refine",
        json={"start_ts": 0, "end_ts": 0},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# GET /api/v1/jobs/{id}/stream — stream_job_status
# ---------------------------------------------------------------------------

def test_stream_job_status_unauthenticated(client: TestClient, session: Session):
    """Streaming without token must be rejected with 401."""
    _, _, job = _create_user_video_job(session, status="COMPLETED")
    resp = client.get(f"/api/v1/jobs/{job.id}/stream")
    assert resp.status_code == 401


def test_stream_job_status_forbidden_when_not_owner(client: TestClient, session: Session):
    """Streaming another user's job must return 403."""
    _, _, job = _create_user_video_job(session, status="COMPLETED")
    other_token = register_and_get_token(client, email="stream_intruder@example.com")

    resp = client.get(f"/api/v1/jobs/{job.id}/stream?token={other_token}")
    assert resp.status_code == 403


def test_stream_job_status_not_found(client: TestClient, engine):
    """
    Streaming a non-existent job UUID returns an SSE response whose first
    data payload contains an 'error' key.

    stream_job_status opens `Session(engine)` directly from app.modules.clips.router
    (bypassing the dependency-injected test session).  We patch that engine
    reference so it uses the test engine, ensuring the job lookup returns None.
    """
    token = register_and_get_token(client, email="stream_nf@example.com")
    random_id = str(uuid.uuid4())

    with patch("app.modules.clips.router.engine", engine):
        resp = client.get(f"/api/v1/jobs/{random_id}/stream?token={token}")

    # The endpoint returns a StreamingResponse regardless; check first chunk.
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("text/event-stream")

    body = resp.text
    # First SSE chunk should contain the error payload
    assert "error" in body


def test_stream_job_status_found(client: TestClient, session: Session, engine):
    """
    Streaming an existing COMPLETED job returns a payload with job_id and status.
    The generator exits after one iteration because status is COMPLETED/done.
    """
    user, _, job = _create_user_video_job(session, status="COMPLETED")
    token = create_access_token(str(user.id))

    with patch("app.modules.clips.router.engine", engine):
        resp = client.get(f"/api/v1/jobs/{job.id}/stream?token={token}")

    assert resp.status_code == 200
    body = resp.text
    assert str(job.id) in body
    assert "COMPLETED" in body


# ---------------------------------------------------------------------------
# Recovery de jobs interrompidos ao reiniciar worker
# ---------------------------------------------------------------------------

def test_recover_interrupted_jobs(session: Session, tmp_path):
    from app.modules.clips.tasks import recover_interrupted_jobs

    video_file = tmp_path / "video.mp4"
    video_file.write_bytes(b"mp4")

    user = User(
        email=f"recover_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("password123"),
        first_name="Rec",
        last_name="Owner",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    video_ok = Video(user_id=user.id, original_filename="v.mp4", storage_path=str(video_file))
    video_missing = Video(user_id=user.id, original_filename="dl.mp4", storage_path=None)
    session.add_all([video_ok, video_missing])
    session.commit()
    session.refresh(video_ok)
    session.refresh(video_missing)

    job_fast = ProcessingJob(video_id=video_ok.id, target_number=10, status="FAST_SCAN")
    job_deep = ProcessingJob(video_id=video_ok.id, target_number=7, status="DEEP_SCAN")
    job_track = ProcessingJob(video_id=video_ok.id, target_number=9, status="EXTRACTING")
    job_dl = ProcessingJob(video_id=video_missing.id, target_number=5, status="DOWNLOADING:42")
    job_done = ProcessingJob(video_id=video_ok.id, target_number=1, status="COMPLETED")
    session.add_all([job_fast, job_deep, job_track, job_dl, job_done])
    session.commit()
    session.refresh(job_track)

    cand = Candidate(
        job_id=job_track.id,
        signature="9_#00ff00",
        name="Jogador 9",
        number=9,
        color_hex="#00ff00",
        is_target=True,
    )
    session.add(cand)
    session.commit()

    with patch("app.modules.clips.tasks.run_fast_scan") as mock_fast:
        with patch("app.modules.clips.tasks.run_deep_scan") as mock_deep:
            with patch("app.modules.clips.tasks.run_full_tracking") as mock_track:
                recovered = recover_interrupted_jobs()

    assert recovered == 3
    mock_fast.delay.assert_called_once_with(job_fast.id, str(video_file), 10, 0, 0)
    mock_deep.delay.assert_called_once_with(job_deep.id, str(video_file), 7, 0, 0)
    mock_track.delay.assert_called_once_with(job_track.id, str(video_file), 9, "9_#00ff00", 0, 0)

    session.refresh(job_dl)
    session.refresh(job_done)
    assert job_dl.status == "ERROR"
    assert job_done.status == "COMPLETED"

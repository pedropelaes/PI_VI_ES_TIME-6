"""
Testes de integração para o fluxo de importação do Google Drive:
- Validação síncrona de metadados (Drive API v3)
- Criação de Video e ProcessingJob com status DOWNLOADING
- Publicação da task Celery download_and_process_drive_video
- Tratamento de erros (401, 403, 404, formato inválido, tamanho excedido)
- Execução e resiliência da task Celery (download streaming e limpeza em falha)
"""
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.identity.models import User
from app.modules.clips.models import Video, ProcessingJob
from app.core.security import hash_password
from app.core.exceptions import UnauthorizedError, ForbiddenError, NotFoundError, BadRequestError


def register_and_get_token(client: TestClient, email: str = "drive_user@example.com") -> str:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "first_name": "Drive",
            "last_name": "Tester",
        },
    )
    assert resp.status_code == 200, f"Registration failed: {resp.text}"
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Testes do Endpoint POST /api/v1/jobs/import/google-drive
# ---------------------------------------------------------------------------

def test_import_google_drive_unauthenticated(client: TestClient):
    """Tentativa de importação sem token JWT deve ser rejeitada com 401."""
    resp = client.post(
        "/api/v1/jobs/import/google-drive",
        json={
            "file_id": "google-drive-file-id-123",
            "google_access_token": "ya29.sample_oauth_token",
            "target_number": 10,
        },
    )
    assert resp.status_code in (401, 403)


def test_import_google_drive_invalid_target_number(client: TestClient):
    """target_number inválido (< 1 ou > 999) deve falhar na validação Pydantic com 422."""
    token = register_and_get_token(client, email="drive_val@example.com")

    resp = client.post(
        "/api/v1/jobs/import/google-drive",
        json={
            "file_id": "file-123",
            "google_access_token": "ya29.valid",
            "target_number": 0,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_import_google_drive_token_expired(client: TestClient):
    """Google API retornando 401 (token expirado) deve resultar em 401 para o cliente."""
    token = register_and_get_token(client, email="drive_expired@example.com")

    with patch("app.modules.clips.router.get_google_drive_file_metadata", side_effect=UnauthorizedError("Token do Google Drive inválido ou expirado.")):
        resp = client.post(
            "/api/v1/jobs/import/google-drive",
            json={
                "file_id": "file-123",
                "google_access_token": "ya29.expired_token",
                "target_number": 10,
            },
            headers=auth_headers(token),
        )

    assert resp.status_code == 401
    assert "Token do Google Drive" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_import_google_drive_permission_denied(client: TestClient):
    """Google API retornando 403 (permissão negada) deve resultar em 403 para o cliente."""
    token = register_and_get_token(client, email="drive_forbidden@example.com")

    with patch("app.modules.clips.router.get_google_drive_file_metadata", side_effect=ForbiddenError("Sem permissão para acessar este arquivo no Google Drive.")):
        resp = client.post(
            "/api/v1/jobs/import/google-drive",
            json={
                "file_id": "file-123",
                "google_access_token": "ya29.no_perm",
                "target_number": 10,
            },
            headers=auth_headers(token),
        )

    assert resp.status_code == 403
    assert "Sem permissão" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_import_google_drive_invalid_format(client: TestClient):
    """Arquivo que não é vídeo deve ser rejeitado com 400."""
    token = register_and_get_token(client, email="drive_mime@example.com")

    with patch("app.modules.clips.router.get_google_drive_file_metadata", side_effect=BadRequestError("O arquivo selecionado não é um formato de vídeo suportado.")):
        resp = client.post(
            "/api/v1/jobs/import/google-drive",
            json={
                "file_id": "file-123",
                "google_access_token": "ya29.valid",
                "target_number": 10,
            },
            headers=auth_headers(token),
        )

    assert resp.status_code == 400
    assert "não é um formato de vídeo suportado" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_import_google_drive_file_too_large(client: TestClient):
    """Arquivo acima do limite configurado deve ser rejeitado com 400."""
    token = register_and_get_token(client, email="drive_large@example.com")

    with patch("app.modules.clips.router.get_google_drive_file_metadata", side_effect=BadRequestError("O arquivo excede o limite máximo permitido.")):
        resp = client.post(
            "/api/v1/jobs/import/google-drive",
            json={
                "file_id": "file-123",
                "google_access_token": "ya29.valid",
                "target_number": 10,
            },
            headers=auth_headers(token),
        )

    assert resp.status_code == 400
    assert "limite máximo permitido" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_import_google_drive_success(client: TestClient, session: Session):
    """Importação válida cria Video, ProcessingJob com status DOWNLOADING e despacha a task Celery."""
    token = register_and_get_token(client, email="drive_success@example.com")

    fake_metadata = {
        "id": "file-123",
        "name": "partida_final.mp4",
        "mimeType": "video/mp4",
        "size": 52428800,  # 50 MB
    }

    with patch("app.modules.clips.router.get_google_drive_file_metadata", new=AsyncMock(return_value=fake_metadata)):
        with patch("app.modules.clips.router.download_and_process_drive_video") as mock_task:
            resp = client.post(
                "/api/v1/jobs/import/google-drive",
                json={
                    "file_id": "file-123",
                    "google_access_token": "ya29.valid_token",
                    "target_number": 7,
                    "start_ts": 10,
                    "end_ts": 60,
                },
                headers=auth_headers(token),
            )

    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "DOWNLOADING"
    mock_task.delay.assert_called_once()

    # Verifica persistência no banco
    job_uuid = uuid.UUID(data["job_id"])
    job = session.get(ProcessingJob, job_uuid)
    assert job is not None
    assert job.status == "DOWNLOADING"
    assert job.target_number == 7

    video = session.get(Video, job.video_id)
    assert video is not None
    assert video.original_filename == "partida_final.mp4"
    assert video.file_size_mb == 50.0


# ---------------------------------------------------------------------------
# Testes da Task Celery download_and_process_drive_video
# ---------------------------------------------------------------------------

def test_download_and_process_drive_video_task_success(session: Session, tmp_path: Path):
    """A task baixa o vídeo em streaming, atualiza o Video e dispara o Fast Scan."""
    from app.modules.clips.tasks import download_and_process_drive_video

    # Cria User, Video e Job no DB
    user = User(
        email=f"task_success_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("pass"),
        first_name="Task",
        last_name="Tester",
    )
    session.add(user)
    session.commit()

    video = Video(
        user_id=user.id,
        original_filename="jogo.mp4",
        storage_path=None,
    )
    session.add(video)
    session.commit()

    job = ProcessingJob(
        video_id=video.id,
        target_number=10,
        status="DOWNLOADING",
    )
    session.add(job)
    session.commit()

    # Mock de storage e download
    fake_video_dest = tmp_path / "jogo.mp4"

    with patch("app.core.storage.LocalStorageBackend.path_for", return_value=fake_video_dest):
        with patch("app.modules.clips.google_drive.download_google_drive_file_streaming", return_value=1048576) as mock_dl:
            with patch("app.modules.clips.tasks.run_fast_scan") as mock_fast_scan:
                download_and_process_drive_video(
                    job_id=job.id,
                    file_id="drive-123",
                    access_token="ya29.token",
                    target_number=10,
                    start_ts=0,
                    end_ts=0,
                )

    mock_dl.assert_called_once()
    mock_fast_scan.delay.assert_called_once_with(job.id, str(fake_video_dest), 10, 0, 0)

    session.refresh(video)
    assert video.storage_path == str(fake_video_dest)
    assert video.file_size_mb == 1.0


def test_download_and_process_drive_video_task_failure(session: Session, tmp_path: Path):
    """Falha durante o download atualiza o status do Job para ERROR e limpa o arquivo corrompido."""
    from app.modules.clips.tasks import download_and_process_drive_video

    user = User(
        email=f"task_fail_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("pass"),
        first_name="Task",
        last_name="Fail",
    )
    session.add(user)
    session.commit()

    video = Video(
        user_id=user.id,
        original_filename="corrompido.mp4",
        storage_path=None,
    )
    session.add(video)
    session.commit()

    job = ProcessingJob(
        video_id=video.id,
        target_number=10,
        status="DOWNLOADING",
    )
    session.add(job)
    session.commit()

    fake_file = tmp_path / "corrompido.mp4"
    fake_file.write_text("corrupted content")

    with patch("app.core.storage.LocalStorageBackend.path_for", return_value=fake_file):
        with patch("app.modules.clips.google_drive.download_google_drive_file_streaming", side_effect=RuntimeError("Connection lost")):
            with patch("app.modules.clips.tasks.run_fast_scan") as mock_fast_scan:
                download_and_process_drive_video(
                    job_id=job.id,
                    file_id="drive-123",
                    access_token="ya29.token",
                    target_number=10,
                    start_ts=0,
                    end_ts=0,
                )

    mock_fast_scan.delay.assert_not_called()

    session.refresh(job)
    assert job.status == "ERROR"
    assert not fake_file.exists()


# ---------------------------------------------------------------------------
# Testes do Endpoint GET /api/v1/jobs/drive-preview/{file_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preview_drive_video_streaming_range(client: TestClient):
    """O endpoint de preview deve repassar o Range header e retornar status 206 com chunks."""
    fake_video_bytes = b"fake video bytes for preview range"

    class FakeResponse:
        status_code = 206
        headers = {
            "Content-Range": "bytes 0-10/34",
            "Content-Length": "11",
            "Content-Type": "video/mp4",
        }

        async def aiter_bytes(self, chunk_size=1024):
            yield fake_video_bytes[:11]

        async def aclose(self):
            pass

    class FakeClient:
        def build_request(self, method, url, headers):
            return {"method": method, "url": url, "headers": headers}

        async def send(self, req, stream=True):
            return FakeResponse()

        async def aclose(self):
            pass

    with patch("httpx.AsyncClient", return_value=FakeClient()):
        resp = client.get(
            "/api/v1/jobs/drive-preview/drive-file-123?access_token=ya29.sample_token",
            headers={"Range": "bytes=0-10"},
        )

    assert resp.status_code == 206
    assert resp.headers.get("accept-ranges") == "bytes"
    assert resp.headers.get("content-range") == "bytes 0-10/34"
    assert resp.headers.get("content-type") == "video/mp4"
    assert resp.content == fake_video_bytes[:11]


@pytest.mark.asyncio
async def test_preview_drive_video_expired_token(client: TestClient):
    """Quando o Google Drive retorna 401 durante o preview, deve retornar 401."""
    class Fake401Response:
        status_code = 401
        headers = {}

        async def aclose(self):
            pass

    class FakeClient:
        def build_request(self, method, url, headers):
            return {}

        async def send(self, req, stream=True):
            return Fake401Response()

        async def aclose(self):
            pass

    with patch("httpx.AsyncClient", return_value=FakeClient()):
        resp = client.get("/api/v1/jobs/drive-preview/drive-file-123?access_token=ya29.expired")

    assert resp.status_code == 401
    assert "Token do Google Drive expirado" in resp.json()["detail"]


"""
Serviço de integração com a Google Drive API v3 para validação de metadados
e download em streaming otimizado (sem alocação de vídeo completo em memória RAM).
"""
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import httpx

from app.core.config import MAX_VIDEO_SIZE_MB, ALLOWED_VIDEO_MIME_TYPES
from app.core.exceptions import (
    NotFoundError,
    ForbiddenError,
    UnauthorizedError,
    BadRequestError,
)

DRIVE_API_BASE_URL = "https://www.googleapis.com/drive/v3/files"


async def get_google_drive_file_metadata(file_id: str, access_token: str) -> Dict[str, Any]:
    """
    Consulta os metadados do arquivo na Google Drive API v3.
    Valida existência, permissão, tipo MIME de vídeo suportado e tamanho máximo.
    Retorna também a duração em milissegundos se disponível em videoMediaMetadata.
    """
    url = f"{DRIVE_API_BASE_URL}/{file_id}"
    params = {"fields": "id,name,size,mimeType,videoMediaMetadata"}
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(url, params=params, headers=headers)
        except httpx.RequestError as exc:
            raise BadRequestError(f"Falha de comunicação com o Google Drive: {exc}") from exc

    if response.status_code == 401:
        raise UnauthorizedError("Token do Google Drive inválido ou expirado. Faça login novamente no Google.")

    if response.status_code == 403:
        raise ForbiddenError("Sem permissão para acessar este arquivo no Google Drive.")

    if response.status_code == 404:
        raise NotFoundError("Arquivo não encontrado no Google Drive.")

    if response.status_code != 200:
        raise BadRequestError(f"Erro ao consultar arquivo no Google Drive (código {response.status_code}).")

    data = response.json()
    mime_type = data.get("mimeType", "")
    name = data.get("name", "video.mp4")
    raw_size = data.get("size")
    video_meta = data.get("videoMediaMetadata") or {}
    duration_millis = video_meta.get("durationMillis")

    # Validar formato
    if mime_type not in ALLOWED_VIDEO_MIME_TYPES:
        raise BadRequestError(
            f"O arquivo selecionado ({name}) não é um formato de vídeo suportado ({mime_type}). "
            "Selecione um arquivo de vídeo (ex.: MP4, MOV, AVI, WebM)."
        )

    # Validar tamanho se fornecido pela API
    if raw_size is not None:
        size_bytes = int(raw_size)
        max_bytes = MAX_VIDEO_SIZE_MB * 1024 * 1024
        if size_bytes > max_bytes:
            raise BadRequestError(
                f"O arquivo excede o limite máximo permitido de {MAX_VIDEO_SIZE_MB}MB."
            )
    else:
        size_bytes = 0

    return {
        "id": data.get("id", file_id),
        "name": name,
        "mimeType": mime_type,
        "size": size_bytes,
        "durationMillis": int(duration_millis) if duration_millis else None,
    }


def download_google_drive_file_streaming(
    file_id: str,
    access_token: str,
    destination_path: Path,
    chunk_size: int = 4 * 1024 * 1024,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> int:
    """
    Realiza o download em streaming do arquivo do Google Drive diretamente para o disco,
    utilizando chunks de 4 MB e buffer otimizado para alta velocidade de transferência
    mantendo baixo o consumo de memória RAM.
    Notifica periodicamente o progresso em bytes através de on_progress(bytes_baixados, total_bytes).
    Usa arquivo temporário (.part) que é renomeado apenas ao concluir o download.
    """
    url = f"{DRIVE_API_BASE_URL}/{file_id}"
    params = {"alt": "media"}
    headers = {"Authorization": f"Bearer {access_token}"}

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination_path.with_suffix(destination_path.suffix + ".part")

    total_bytes = 0
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(connect=20.0, read=60.0, write=None, pool=None),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        ) as client:
            with client.stream("GET", url, params=params, headers=headers) as response:
                if response.status_code == 401:
                    raise UnauthorizedError("Token do Google expirado durante o download.")
                if response.status_code == 403:
                    raise ForbiddenError("Acesso negado ao baixar arquivo do Google Drive.")
                if response.status_code == 404:
                    raise NotFoundError("Arquivo não encontrado no Google Drive durante o download.")
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))

                with open(temp_path, "wb", buffering=4 * 1024 * 1024) as f:
                    for chunk in response.iter_bytes(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            total_bytes += len(chunk)
                            if on_progress:
                                on_progress(total_bytes, total_size)

        # Download completo: substitui pelo caminho final atomicamente
        temp_path.replace(destination_path)
        return total_bytes

    except Exception:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise

import json
import subprocess
from pathlib import Path
from typing import Callable

SUPPORTED_CODECS = {"h264"}


def get_video_codec(path: Path) -> str:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    streams = json.loads(probe.stdout).get("streams", [])
    if not streams:
        raise ValueError(f"Nenhuma faixa de vídeo encontrada em {path.name}")
    return streams[0]["codec_name"]


def ensure_h264(
    path: Path,
    on_converting: Callable[[], None] | None = None,
) -> Path:
    """Converte para H.264 se o codec não for suportado pelo OpenCV (ex.: AV1).
    Retorna o caminho do arquivo final (o original é removido se convertido)."""
    codec = get_video_codec(path)
    if codec in SUPPORTED_CODECS:
        return path

    if on_converting:
        on_converting()

    print(f"[VIDEO] Codec '{codec}' não suportado. Convertendo {path.name} para H.264...")
    out = path.with_name(f"{path.stem}_h264.mp4")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(path),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
             "-c:a", "aac", str(out)],
            check=True,
        )
    except Exception:
        out.unlink(missing_ok=True)
        raise
    path.unlink(missing_ok=True)
    print(f"[VIDEO] Conversão concluída: {out.name}")
    return out
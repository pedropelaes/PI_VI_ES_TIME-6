"""
Configurações do app: paths, JWT e modelo YOLO.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Diretório base do backend
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Modelo YOLO para tracking (treinado para futebol)
YOLO_MODEL_PATH = BACKEND_DIR / "weights" / "best.pt"

# Auth / JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production-use-env")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas

# Limites de upload / importação de vídeo
MAX_VIDEO_SIZE_MB = int(os.getenv("MAX_VIDEO_SIZE_MB", "20048"))  # 2 GB padrão
ALLOWED_VIDEO_MIME_TYPES = (
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
    "video/x-matroska",
    "video/mpeg",
)

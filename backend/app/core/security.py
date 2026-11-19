"""
Segurança: hash de senha (bcrypt), geração/validação de JWT e cifra de tokens.
"""
import base64
import binascii
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import JWT_ALGORITHM, JWT_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES

# bcrypt tem limite de 72 bytes
BCRYPT_MAX_BYTES = 72


def _to_b72(password: str) -> bytes:
    """Garante que a senha em bytes não ultrapasse 72 bytes (limite do bcrypt)."""
    raw = password.encode("utf-8")
    return raw[:BCRYPT_MAX_BYTES] if len(raw) > BCRYPT_MAX_BYTES else raw


def hash_password(password: str) -> str:
    """Gera hash bcrypt da senha."""
    pwd_bytes = _to_b72(password)
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto plano confere com o hash."""
    pwd_bytes = _to_b72(plain_password)
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))


def create_access_token(subject: str | Any) -> str:
    """Cria um JWT com o subject (ex.: user_id) e expiração."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(subject), "exp": expire}
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Decodifica o JWT e retorna o subject (user_id) ou None se inválido."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


_DRIVE_TOKEN_PREFIX = "enc:"


def _drive_keys() -> tuple[bytes, bytes]:
    secret = JWT_SECRET_KEY.encode("utf-8")
    enc_key = hashlib.sha256(b"drive-enc:" + secret).digest()
    mac_key = hashlib.sha256(b"drive-mac:" + secret).digest()
    return enc_key, mac_key


def _drive_xor_stream(enc_key: bytes, iv: bytes, data: bytes) -> bytes:
    out = bytearray(len(data))
    offset = 0
    counter = 0
    while offset < len(data):
        block = hashlib.sha256(enc_key + iv + counter.to_bytes(4, "big")).digest()
        chunk_len = min(len(block), len(data) - offset)
        for i in range(chunk_len):
            out[offset + i] = data[offset + i] ^ block[i]
        offset += chunk_len
        counter += 1
    return bytes(out)


def encrypt_drive_token(plain_token: str) -> str:
    """Criptografa um token OAuth antes de enfileirá-lo no broker Redis."""
    enc_key, mac_key = _drive_keys()
    iv = os.urandom(16)
    ciphertext = _drive_xor_stream(enc_key, iv, plain_token.encode("utf-8"))
    tag = hmac.new(mac_key, iv + ciphertext, hashlib.sha256).digest()
    payload = base64.urlsafe_b64encode(iv + ciphertext + tag).decode("ascii")
    return f"{_DRIVE_TOKEN_PREFIX}{payload}"


def decrypt_drive_token(token: str) -> str:
    """Descriptografa token OAuth recebido via task Celery; aceita texto puro legado."""
    if not token.startswith(_DRIVE_TOKEN_PREFIX):
        return token

    try:
        raw = base64.urlsafe_b64decode(token[len(_DRIVE_TOKEN_PREFIX):].encode("ascii"))
    except (binascii.Error, ValueError, UnicodeError) as exc:
        raise ValueError("Token criptografado inválido.") from exc

    if len(raw) < 48:
        raise ValueError("Token criptografado inválido.")

    iv = raw[:16]
    ciphertext = raw[16:-32]
    tag = raw[-32:]
    enc_key, mac_key = _drive_keys()
    expected_tag = hmac.new(mac_key, iv + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Token criptografado inválido ou adulterado.")

    try:
        return _drive_xor_stream(enc_key, iv, ciphertext).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Token criptografado inválido.") from exc

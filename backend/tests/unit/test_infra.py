"""
Guarda-trilho da infraestrutura: prova que o loop rapido de TDD nao precisa de banco.

Se alguem mover uma fixture com dependencia de Postgres para `tests/conftest.py`, este
arquivo passa a falhar com o `postgres-test` desligado -- que e exatamente o sintoma
que queremos detectar cedo.
"""
from app.core.security import (
    decrypt_drive_token,
    encrypt_drive_token,
    hash_password,
    verify_password,
)


def test_hash_de_senha_confere():
    hashed = hash_password("senha12345")

    assert hashed != "senha12345"
    assert verify_password("senha12345", hashed)
    assert not verify_password("senha-errada", hashed)


def test_bcrypt_trunca_em_72_bytes():
    """bcrypt ignora o que passa de 72 bytes; o helper trunca antes de hashear."""
    longa = "a" * 80

    assert verify_password("a" * 72, hash_password(longa))


def test_encrypt_and_decrypt_drive_token():
    import pytest

    plain = "ya29.a0AfH6SMC_sample_google_oauth_token"
    encrypted = encrypt_drive_token(plain)

    assert encrypted.startswith("enc:")
    assert plain not in encrypted
    assert decrypt_drive_token(encrypted) == plain
    assert decrypt_drive_token(plain) == plain

    tampered = encrypted[:-4] + ("AAAA" if not encrypted.endswith("AAAA") else "BBBB")
    with pytest.raises(ValueError):
        decrypt_drive_token(tampered)

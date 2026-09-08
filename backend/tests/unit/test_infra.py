"""
Guarda-trilho da infraestrutura: prova que o loop rapido de TDD nao precisa de banco.

Se alguem mover uma fixture com dependencia de Postgres para `tests/conftest.py`, este
arquivo passa a falhar com o `postgres-test` desligado -- que e exatamente o sintoma
que queremos detectar cedo.
"""
from app.core.security import hash_password, verify_password


def test_hash_de_senha_confere():
    hashed = hash_password("senha12345")

    assert hashed != "senha12345"
    assert verify_password("senha12345", hashed)
    assert not verify_password("senha-errada", hashed)


def test_bcrypt_trunca_em_72_bytes():
    """bcrypt ignora o que passa de 72 bytes; o helper trunca antes de hashear."""
    longa = "a" * 80

    assert verify_password("a" * 72, hash_password(longa))

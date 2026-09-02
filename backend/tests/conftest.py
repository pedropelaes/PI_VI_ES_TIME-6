"""
Fixtures da suite.

A primeira coisa que este arquivo faz e apontar DATABASE_URL para o banco de teste,
ANTES de qualquer import de `app.*`. E obrigatorio nessa ordem: `app/core/database.py`
le DATABASE_URL no momento do import e cria a engine ali. O `load_dotenv()` que roda
dentro daquele modulo nao sobrescreve variaveis ja definidas (override=False e o padrao),
entao o valor abaixo vence o backend/.env.
"""
import os
import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://smartscout:smartscout@postgres-test:5432/smartscout_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlmodel import Session  # noqa: E402

from app.core.database import engine as app_engine, get_session  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.identity.models import User  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    """
    Zera o schema e o reconstroi rodando `alembic upgrade head`.

    Usar as migracoes em vez de SQLModel.metadata.create_all e o ponto central do P5:
    uma migracao quebrada falha aqui, e nao no deploy.
    """
    with app_engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        check=True,
        env=os.environ.copy(),
    )

    return app_engine


@pytest.fixture(autouse=True)
def _limpa_tabelas(engine):
    """Esvazia as tabelas depois de cada teste, preservando alembic_version."""
    yield
    with engine.begin() as conn:
        tabelas = list(
            conn.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
                )
            ).scalars()
        )
        if tabelas:
            alvos = ", ".join(f'"{t}"' for t in tabelas)
            conn.execute(text(f"TRUNCATE {alvos} RESTART IDENTITY CASCADE"))


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def usuario(session) -> User:
    user = User(
        email="atleta@teste.com",
        password_hash=hash_password("senha12345"),
        first_name="Jeh",
        last_name="Rodrigues",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def auth_headers(usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(usuario.id))}"}

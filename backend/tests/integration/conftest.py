"""
Fixtures que dependem de Postgres.

Ficam restritas ao pacote `integration` de proposito: os testes em `tests/unit/` nao
podem exigir banco no ar. Se alguma destas fixtures subir para `tests/conftest.py`,
`pytest tests/unit` passa a falhar com o `postgres-test` desligado.
"""
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlmodel import Session

from app.core.database import engine as app_engine
from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.identity.models import User

BACKEND_DIR = Path(__file__).resolve().parents[2]


def exige_banco_de_teste(url: URL) -> None:
    """
    Aborta se a URL nao apontar para um banco descartavel.

    A fixture `engine` roda `DROP SCHEMA public CASCADE`. O banco real do projeto e um
    Postgres gerenciado (Supabase) cujo database chama `postgres`; rodar a suite contra
    ele destruiria producao. Exigir o sufixo `_test` no nome do database torna esse
    acidente impossivel, em vez de apenas improvavel.
    """
    nome = url.database or ""
    if not nome.endswith("_test"):
        raise RuntimeError(
            f"Recusando destruir o schema do banco {nome!r} em {url.host!r}: "
            f"a suite so roda contra um database cujo nome termina em '_test'. "
            f"Verifique TEST_DATABASE_URL."
        )


def url_validada_para_migracao(url: URL) -> str:
    """
    Valida a URL e a serializa para ser passada explicitamente ao subprocesso do Alembic.

    `alembic upgrade head` roda fora do processo do pytest e, por conta propria, resolveria
    a URL em `alembic/env.py` -- que faz `load_dotenv(backend/.env)` e le DATABASE_URL. Isso
    so nao aponta para producao porque `load_dotenv` usa `override=False` por padrao: uma
    palavra trocada naquele arquivo mandaria as migracoes para o Supabase enquanto a guarda
    aqui continuaria passando, porque ela valida a engine da aplicacao, nao a do subprocesso.

    Passando a URL ja validada via `alembic -x db_url=...` (que tem precedencia sobre o
    ambiente em env.py), o alvo do subprocesso e exatamente o que esta guarda aprovou.
    """
    exige_banco_de_teste(url)
    return url.render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def engine():
    """
    Zera o schema e o reconstroi rodando `alembic upgrade head`.

    Usar as migracoes em vez de SQLModel.metadata.create_all e o ponto central do P5:
    uma migracao quebrada falha aqui, e nao no deploy.
    """
    url_migracao = url_validada_para_migracao(app_engine.url)

    with app_engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    subprocess.run(
        ["alembic", "-x", f"db_url={url_migracao}", "upgrade", "head"],
        cwd=BACKEND_DIR,
        check=True,
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
def client(engine):
    """
    TestClient sem override de dependencia: os handlers usam o `get_session` de producao.

    A engine da aplicacao ja e a de teste (tests/conftest.py aponta DATABASE_URL para o
    postgres-test antes de qualquer import de `app.*`), entao qualquer override aqui apenas
    reimplementaria `get_session` -- e no dia em que ele ganhar algo (um `SET LOCAL`, um
    begin() explicito, uma unidade de trabalho por request), a suite continuaria exercitando
    a copia velha e nao o codigo real. A fixture so garante que o schema existe.

    O que ela deliberadamente NAO faz e reaproveitar a Session do teste: isso daria ao
    handler o mesmo identity map do corpo do teste, e um endpoint que esquece o commit()
    passaria a ficar verde. `test_fixtures.py` fixa essa propriedade.
    """
    with TestClient(app) as c:
        yield c


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

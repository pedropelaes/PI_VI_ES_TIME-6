"""
Prova que o schema de teste nasce das migracoes Alembic, e nao de create_all.
Se este teste passar, toda a suite esta exercitando as migracoes (P5 da spec).
"""
import os
import subprocess

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from tests.integration.conftest import (
    BACKEND_DIR,
    exige_banco_de_teste,
    url_validada_para_migracao,
)

# Primeira migracao da pilha, anterior a qualquer coluna adicionada depois. Serve de alvo
# fixo para testes que precisam voltar o schema no tempo sem depender de quantas migracoes
# existem hoje.
BASELINE = "dc5867a2d8e8"


def test_schema_foi_criado_pelas_migracoes(engine):
    with engine.connect() as conn:
        versao = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()

    assert versao is not None, "alembic_version vazia: o schema nao veio das migracoes"


def test_tabelas_da_baseline_existem(engine):
    with engine.connect() as conn:
        tabelas = set(
            conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            ).scalars()
        )

    assert {"users", "videos", "processing_jobs", "clips", "candidates"} <= tabelas


def test_guarda_recusa_banco_que_nao_e_de_teste():
    """O nome do banco real (Supabase) e `postgres`: a guarda tem que barrar."""
    url = make_url("postgresql://postgres.abc:senha@aws.pooler.supabase.com:5432/postgres")

    with pytest.raises(RuntimeError, match="Recusando destruir o schema"):
        exige_banco_de_teste(url)


def test_guarda_menciona_o_banco_encontrado():
    url = make_url("postgresql://u:p@db.exemplo.com:5432/producao")

    with pytest.raises(RuntimeError) as erro:
        exige_banco_de_teste(url)

    assert "'producao'" in str(erro.value)
    assert "db.exemplo.com" in str(erro.value)


def test_guarda_aceita_o_banco_de_teste(engine):
    """Nao pode ter falso positivo: o alvo real da suite passa pela guarda."""
    exige_banco_de_teste(engine.url)
    assert engine.url.database.endswith("_test")


# ---------------------------------------------------------------------------
# A guarda tambem cobre o subprocesso do Alembic
# ---------------------------------------------------------------------------

def test_url_de_migracao_passa_pela_guarda():
    """O que vai para o subprocesso do Alembic e validado antes de sair daqui."""
    url = make_url("postgresql://postgres.abc:senha@aws.pooler.supabase.com:5432/postgres")

    with pytest.raises(RuntimeError, match="Recusando destruir o schema"):
        url_validada_para_migracao(url)


def test_url_de_migracao_preserva_a_senha(engine):
    """Serializar com a senha mascarada faria o subprocesso falhar ao conectar."""
    serializada = url_validada_para_migracao(engine.url)

    assert make_url(serializada).password == engine.url.password


def test_alembic_aceita_senha_com_percent():
    """
    `%` na URL nao pode virar sintaxe de interpolacao do ConfigParser.

    `config.set_main_option` em alembic/env.py escreve num ConfigParser com
    BasicInterpolation; um `%` cru estoura ali, antes de qualquer conexao. E URLs codificam
    senha com percent-encoding, entao qualquer senha gerada com `@`, `%` ou `/` cai nesse
    caso -- com um ValueError que nao menciona senha nenhuma.

    A conexao aqui falha de proposito (porta 1, credencial falsa): o que importa e *como*
    falha. Se o escape sumir de env.py, o erro passa a ser de interpolacao e este teste pega.
    """
    url = "postgresql://usr:p%40ss%25word@127.0.0.1:1/x_test"

    resultado = subprocess.run(
        ["alembic", "-x", f"db_url={url}", "current"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )

    assert "interpolation" not in resultado.stderr.lower(), resultado.stderr[-1500:]


def test_alembic_ignora_database_url_do_ambiente(engine):
    """
    Prova de fogo: com DATABASE_URL apontando para um host inexistente, o subprocesso
    ainda alcanca o banco de teste -- porque usa a URL validada que passamos, e nao o
    ambiente. Se `-x db_url` deixasse de ter precedencia em alembic/env.py, o alembic
    tentaria conectar no host falso e este teste falharia.
    """
    ambiente_envenenado = dict(
        os.environ,
        DATABASE_URL="postgresql://ninguem:nada@host-que-nao-existe.invalid:5432/postgres",
    )

    resultado = subprocess.run(
        ["alembic", "-x", f"db_url={url_validada_para_migracao(engine.url)}", "current"],
        cwd=BACKEND_DIR,
        env=ambiente_envenenado,
        capture_output=True,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr[-1500:]
    assert "host-que-nao-existe" not in resultado.stderr


# ---------------------------------------------------------------------------
# Coluna `role` em users (Task 4)
# ---------------------------------------------------------------------------

def test_users_tem_coluna_role_nao_nula(engine):
    with engine.connect() as conn:
        linha = conn.execute(
            text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name = 'users' AND column_name = 'role'"
            )
        ).first()

    assert linha is not None, "coluna role nao existe em users"
    assert linha[0] == "NO"


def test_novo_usuario_sem_role_recebe_athlete_por_default(engine):
    """
    Cobre o default do lado Python (`Field(default=UserRole.ATHLETE)`) e o round-trip
    do enum pelo psycopg2 -- nao o backfill SQL, que vive no teste abaixo.
    """
    from app.modules.identity.models import User, UserRole
    from app.core.security import hash_password
    from sqlmodel import Session

    with Session(engine) as s:
        user = User(
            email="backfill@teste.com",
            password_hash=hash_password("senha12345"),
            first_name="Bia",
            last_name="Lima",
        )
        s.add(user)
        s.commit()
        s.refresh(user)

        assert user.role == UserRole.ATHLETE


def test_backfill_preenche_linhas_que_existiam_antes_da_migracao(engine):
    """
    A propriedade que justifica a migracao em tres passos (risco PR5).

    O banco real e um Postgres externo com usuarios ja gravados. Adicionar `role` direto
    como NOT NULL falharia la. Aqui a migracao e rodada de verdade sobre uma linha que
    existia antes dela: se alguem trocar os tres passos por um `add_column(nullable=False)`,
    este teste quebra -- os outros dois continuariam verdes, porque a base de teste esta
    sempre vazia quando a suite sobe.
    """
    url = url_validada_para_migracao(engine.url)

    def alembic(*args: str) -> None:
        resultado = subprocess.run(
            ["alembic", "-x", f"db_url={url}", *args],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
        )
        assert resultado.returncode == 0, resultado.stderr[-1500:]

    try:
        # Alvo fixo, nao "-1": a partir da Task 6 o topo da pilha e outra migracao, e um
        # downgrade relativo deixaria de remover `role`. A baseline e o unico ponto que
        # sempre descreve um `users` sem a coluna.
        alembic("downgrade", BASELINE)

        with engine.begin() as conn:
            sobrou = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = 'users' AND column_name = 'role'"
                )
            ).first()
            assert sobrou is None, "o downgrade nao removeu a coluna role"

            conn.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, first_name, last_name,"
                    " max_clips_allowed, created_at) VALUES"
                    " (gen_random_uuid(), 'antigo@teste.com', 'x', 'Ana', 'Antiga', 20, now())"
                )
            )
    finally:
        alembic("upgrade", "head")

    with engine.connect() as conn:
        papel = conn.execute(
            text("SELECT role FROM users WHERE email = 'antigo@teste.com'")
        ).scalar()

    assert papel == "ATHLETE"

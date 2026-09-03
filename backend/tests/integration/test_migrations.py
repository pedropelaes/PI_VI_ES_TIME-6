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

    assert "***" not in serializada
    assert serializada.endswith(engine.url.database)


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

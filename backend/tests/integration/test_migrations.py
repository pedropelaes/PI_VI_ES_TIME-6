"""
Prova que o schema de teste nasce das migracoes Alembic, e nao de create_all.
Se este teste passar, toda a suite esta exercitando as migracoes (P5 da spec).
"""
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from tests.integration.conftest import exige_banco_de_teste


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

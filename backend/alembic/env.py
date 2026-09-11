import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlmodel import SQLModel
from dotenv import load_dotenv

from alembic import context

# --- Projeto no sys.path para importar `app.*` ---------------------------------
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
for _p in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

load_dotenv(BACKEND_DIR / ".env")

# --- Importa os models para registrar todas as tabelas na metadata ------------
import app.modules.identity.models  # noqa: F401,E402
import app.modules.clips.models  # noqa: F401,E402
import app.modules.profiles.models  # noqa: F401,E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# URL do banco: `-x db_url=...` na linha de comando vence tudo; senao vem do ambiente
# (backend/.env), nunca hardcoded no alembic.ini.
#
# O `-x` existe para quem chama o alembic como subprocesso e precisa de certeza sobre o
# alvo -- a suite de testes, por exemplo. Depender so de DATABASE_URL deixaria o alvo
# refem da precedencia do `load_dotenv` acima: trocar `override=False` (o padrao) por
# `override=True` faria o backend/.env de producao vencer silenciosamente.
#
# O `.replace("%", "%%")` nao e supersticao: set_main_option escreve num ConfigParser com
# BasicInterpolation, entao um `%` cru no valor estoura ali mesmo, com
# "invalid interpolation syntax" -- e URLs codificam senha com percent-encoding (`@` vira
# `%40`, `%` vira `%25`). Sem o escape, qualquer senha gerada quebra o alembic com um erro
# que nao menciona senha nenhuma. Escapar aqui, no unico ponto onde o valor e escrito,
# cobre tanto o `-x db_url` quanto o DATABASE_URL do ambiente.
_x_args = context.get_x_argument(as_dictionary=True)
_db_url = _x_args.get("db_url") or os.environ["DATABASE_URL"]
config.set_main_option("sqlalchemy.url", _db_url.replace("%", "%%"))

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata alvo para autogenerate.
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Uso interno de geração de baseline: refletir contra um schema vazio.
        _probe = os.environ.get("ALEMBIC_SEARCH_PATH")
        if _probe:
            from sqlalchemy import text

            connection.execute(text(f"SET search_path TO {_probe}"))

        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

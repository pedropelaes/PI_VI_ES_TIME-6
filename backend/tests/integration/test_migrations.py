"""
Prova que o schema de teste nasce das migracoes Alembic, e nao de create_all.
Se este teste passar, toda a suite esta exercitando as migracoes (P5 da spec).
"""
import importlib.util
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

# Ultima migracao antes de `athlete_profiles`: `users` ja tem `role`, mas nenhum perfil
# existe ainda. Alvo fixo pelo mesmo motivo da BASELINE -- um "-1" passaria a apontar para
# outra migracao assim que a proxima entrar na pilha.
ANTES_DOS_PERFIS = "fe2302746d6a"


def roda_alembic(url: str, *args: str) -> None:
    """Executa o alembic como subprocesso contra a URL ja validada, exigindo sucesso."""
    resultado = subprocess.run(
        ["alembic", "-x", f"db_url={url}", *args],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr[-1500:]


def carrega_migracao(sufixo_do_arquivo: str):
    """
    Importa um modulo de migracao pelo nome do arquivo (o hash da revisao e gerado).

    Serve para os testes reusarem o SQL exato que a migracao roda, em vez de uma copia
    colada que pode divergir dela sem ninguem perceber.
    """
    caminhos = sorted((BACKEND_DIR / "alembic" / "versions").glob(f"*{sufixo_do_arquivo}"))
    assert caminhos, f"nenhuma migracao casa com *{sufixo_do_arquivo}"
    assert len(caminhos) == 1, f"mais de uma migracao casa com *{sufixo_do_arquivo}"

    spec = importlib.util.spec_from_file_location(caminhos[0].stem, caminhos[0])
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


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
        roda_alembic(url, *args)

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


# ---------------------------------------------------------------------------
# Tabela `athlete_profiles` (Task 6)
# ---------------------------------------------------------------------------

def test_athlete_profiles_existe_com_pk_em_user_id(engine):
    with engine.connect() as conn:
        colunas = {
            linha[0]: linha[1]
            for linha in conn.execute(
                text(
                    "SELECT column_name, is_nullable FROM information_schema.columns "
                    "WHERE table_name = 'athlete_profiles'"
                )
            )
        }

    assert colunas, "tabela athlete_profiles nao existe"
    assert colunas["user_id"] == "NO"
    assert colunas["status"] == "NO"
    assert colunas["birth_date"] == "YES"
    assert "age" not in colunas, "idade e derivada de birth_date, nunca uma coluna"

    with engine.connect() as conn:
        pk = list(
            conn.execute(
                text(
                    "SELECT a.attname FROM pg_index i "
                    "JOIN pg_attribute a ON a.attrelid = i.indrelid "
                    "AND a.attnum = ANY(i.indkey) "
                    "WHERE i.indrelid = 'athlete_profiles'::regclass AND i.indisprimary"
                )
            ).scalars()
        )

    assert pk == ["user_id"], f"a PK deveria ser user_id, e {pk}"


def test_perfil_gravado_pelo_orm_volta_com_os_enums(engine, usuario):
    """
    O tipo nativo se chama `athleteposition` e a classe Python, `Position`. Se essa
    ligacao quebrar (ou o round-trip do enum pelo psycopg2 falhar), o erro aparece aqui e
    nao no primeiro endpoint que gravar perfil.
    """
    from sqlmodel import Session

    from app.modules.profiles.models import AthleteProfile, AthleteStatus, Position

    with Session(engine) as s:
        s.add(AthleteProfile(user_id=usuario.id, position=Position.ATACANTE))
        s.commit()

        perfil = s.get(AthleteProfile, usuario.id)

        assert perfil.position is Position.ATACANTE
        assert perfil.status is AthleteStatus.DISPONIVEL
        assert perfil.birth_date is None


def test_backfill_cria_perfil_para_atleta_que_existia_antes_da_migracao(engine):
    """
    A propriedade que o `INSERT ... SELECT` da migracao existe para garantir (secao 5.1 da
    spec de origem): todo usuario ATHLETE precisa de perfil, inclusive os que ja estavam
    gravados antes da migracao rodar.

    A base de teste esta vazia quando a suite sobe, entao um teste que apenas olhasse a
    tabela depois do `upgrade head` passaria mesmo sem backfill nenhum. Aqui a migracao roda
    de verdade sobre linhas inseridas antes dela: apagar o backfill quebra este teste.

    O usuario SCOUT esta aqui de proposito -- o backfill nao pode inventar perfil de atleta
    para quem nao e atleta.
    """
    url = url_validada_para_migracao(engine.url)

    try:
        roda_alembic(url, "downgrade", ANTES_DOS_PERFIS)

        with engine.begin() as conn:
            sobrou = conn.execute(
                text("SELECT to_regclass('public.athlete_profiles')")
            ).scalar()
            assert sobrou is None, "o downgrade nao removeu a tabela athlete_profiles"

            conn.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, first_name, last_name,"
                    " role, max_clips_allowed, created_at) VALUES"
                    " (gen_random_uuid(), 'atleta.antigo@teste.com', 'x', 'Ana', 'Antiga',"
                    " 'ATHLETE', 20, now()),"
                    " (gen_random_uuid(), 'olheiro.antigo@teste.com', 'x', 'Bo', 'Antigo',"
                    " 'SCOUT', 20, now())"
                )
            )
    finally:
        roda_alembic(url, "upgrade", "head")

    with engine.connect() as conn:
        perfis = {
            linha[0]: linha[1]
            for linha in conn.execute(
                text(
                    "SELECT u.email, p.status FROM athlete_profiles p"
                    " JOIN users u ON u.id = p.user_id"
                )
            )
        }

    assert "atleta.antigo@teste.com" in perfis, (
        "o backfill nao criou perfil para o atleta que existia antes da migracao"
    )
    assert perfis["atleta.antigo@teste.com"] == "DISPONIVEL"
    assert "olheiro.antigo@teste.com" not in perfis, (
        "o backfill criou perfil de atleta para um usuario SCOUT"
    )


def test_backfill_e_idempotente(engine):
    """
    O `ON CONFLICT DO NOTHING` da migracao (risco PR5): rodar o backfill de novo sobre uma
    tabela ja populada nao pode estourar chave duplicada nem duplicar perfil.

    O SQL vem do proprio modulo da migracao, e nao de uma copia colada aqui -- se alguem
    tirar o ON CONFLICT de la, este teste falha com o UniqueViolation real.
    """
    migracao = carrega_migracao("_cria_athlete_profiles.py")

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, first_name, last_name,"
                " role, max_clips_allowed, created_at) VALUES"
                " (gen_random_uuid(), 'atleta.idem@teste.com', 'x', 'Cid', 'Idem',"
                " 'ATHLETE', 20, now())"
            )
        )

    for _ in range(2):
        with engine.begin() as conn:
            conn.execute(text(migracao.BACKFILL_ATLETAS))

    with engine.connect() as conn:
        quantidade = conn.execute(
            text(
                "SELECT count(*) FROM athlete_profiles p JOIN users u ON u.id = p.user_id"
                " WHERE u.email = 'atleta.idem@teste.com'"
            )
        ).scalar()

    assert quantidade == 1

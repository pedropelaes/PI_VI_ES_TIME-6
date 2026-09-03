# Perfil do Atleta — Fatia 1 (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer a página de perfil do atleta renderizar identidade e estatísticas reais vindas do backend, substituindo os dados mockados.

**Architecture:** Backend ganha o módulo `profiles` com a anatomia completa (`router` · `service` · `repository` · `models` · `schemas`) — o primeiro do projeto a separar regra de negócio de acesso a dados, que é o que torna o teste unitário com repository fake possível. `users` ganha `role`, e cada atleta ganha uma linha 1:1 em `athlete_profiles`. No frontend entra a primeira fatia do F3: `shared/lib/httpClient` e `features/profiles/`, com TanStack Query, sem tocar em `services/api.ts`.

**Tech Stack:** FastAPI 0.133 · SQLModel 0.0.37 · Alembic · PostgreSQL · pytest · React 19 · TypeScript 5.9 · Vite 7.3 · TanStack Query · Vitest

**Spec:** `docs/superpowers/specs/2026-09-02-perfil-publico-atleta-design.md`

---

---

> ## ⚠️ Alembic aponta para PRODUCAO por padrao
>
> O `DATABASE_URL` do container `api` e o Supabase **real**. O `alembic/env.py` usa essa
> variavel quando nao recebe `-x db_url=`, e apenas o processo do pytest a reescreve.
> Portanto `docker compose exec api alembic downgrade ...` **roda contra producao**.
>
> Toda invocacao de Alembic que toque o schema deve passar o banco de teste explicitamente:
>
> ```bash
> docker compose exec api alembic -x db_url=postgresql://smartscout:smartscout@postgres-test:5432/smartscout_test upgrade head
> ```
>
> `alembic revision -m "..."` (sem `--autogenerate`) nao conecta em banco nenhum e e seguro.

---

## Estrutura de arquivos

**Backend — criados**

| Arquivo | Responsabilidade |
|---|---|
| `backend/requirements/dev.txt` | dependências só de teste |
| `backend/pytest.ini` | configuração do pytest |
| `backend/tests/conftest.py` | apenas o setup de `DATABASE_URL`, que precisa ocorrer antes de qualquer import de `app.*` |
| `backend/tests/integration/conftest.py` | fixtures que dependem de banco: engine migrada com guarda de destino, sessão, client, usuário autenticado |
| `backend/tests/unit/test_infra.py` | teste puro que falha se algum fixture de banco voltar ao conftest compartilhado |
| `backend/tests/integration/test_auth_caracterizacao.py` | trava o comportamento atual de register/login |
| `backend/tests/integration/test_migrations.py` | prova que o schema veio das migrações |
| `backend/app/modules/profiles/__init__.py` | pacote |
| `backend/app/modules/profiles/models.py` | `AthleteProfile` + enums do domínio |
| `backend/app/modules/profiles/repository.py` | `AthleteProfileRecord`, `Protocol`, implementação SQL |
| `backend/app/modules/profiles/service.py` | regra: idade, erros de domínio, atualização parcial |
| `backend/app/modules/profiles/schemas.py` | DTOs de entrada e saída |
| `backend/app/modules/profiles/router.py` | HTTP, sem regra |
| `backend/tests/unit/test_profiles_service.py` | service com repository fake |
| `backend/tests/integration/test_profiles_router.py` | rotas com TestClient |

**Backend — modificados**

| Arquivo | Mudança |
|---|---|
| `docker-compose.yml` | serviço `postgres-test` |
| `backend/Dockerfile` | instala `requirements/dev.txt` |
| `backend/alembic/env.py:24` | importa os models de `profiles` |
| `backend/app/modules/identity/models.py` | `User.role` |
| `backend/app/modules/identity/schemas.py` | `role` em `UserCreate` e `UserResponse` |
| `backend/app/modules/identity/router.py` | register valida `role` e cria o perfil |
| `backend/app/main.py` | monta o router de `profiles` |

**Frontend — criados**

| Arquivo | Responsabilidade |
|---|---|
| `frontend/src/test/setup.ts` | setup do Testing Library |
| `frontend/src/shared/lib/httpClient.ts` | fetch com JWT, timeout e erro tipado |
| `frontend/src/shared/lib/httpClient.test.ts` | testes do client |
| `frontend/src/shared/lib/queryClient.ts` | configuração do TanStack Query |
| `frontend/src/features/profiles/types.ts` | DTO da API e view model |
| `frontend/src/features/profiles/mappers.ts` | funções puras de formatação |
| `frontend/src/features/profiles/mappers.test.ts` | testes dos mappers |
| `frontend/src/features/profiles/api.ts` | chamadas do módulo |
| `frontend/src/features/profiles/hooks/useAthleteProfile.ts` | hook de leitura |
| `frontend/src/features/profiles/hooks/useAthleteProfile.test.tsx` | testes do hook |
| `frontend/src/features/profiles/components/ProfileHeader.tsx` | cabeçalho |
| `frontend/src/features/profiles/components/QuickStats.tsx` | grade de estatísticas |
| `frontend/src/features/profiles/components/AboutTab.tsx` | aba Sobre |

**Frontend — modificados**

| Arquivo | Mudança |
|---|---|
| `frontend/package.json` | deps e script `test` |
| `frontend/vite.config.js` | bloco `test` do Vitest |
| `frontend/src/main.tsx` | `QueryClientProvider` |
| `frontend/src/App.tsx:26` | rota `/athletes/:userId` |
| `frontend/src/pages/PublicProfile/PublicProfile.tsx` | consome os hooks |

---

## Bloco A — Infraestrutura de testes

### Task 1: Banco de teste e dependências

**Files:**
- Create: `backend/requirements/dev.txt`
- Modify: `docker-compose.yml`
- Modify: `backend/Dockerfile`

- [ ] **Step 1: Criar `backend/requirements/dev.txt`**

```
-r api.txt
pytest==8.4.2
httpx==0.28.1
```

`httpx` é exigido pelo `TestClient` do Starlette; sem ele o import falha.

- [ ] **Step 2: Instalar as dependências de teste na imagem**

Em `backend/Dockerfile`, trocar a linha `RUN pip install --no-cache-dir -r requirements/api.txt` por:

```dockerfile
RUN pip install --no-cache-dir -r requirements/dev.txt
```

`dev.txt` inclui `api.txt`, então a imagem continua com tudo que a API precisa e ganha pytest.
Esta é a imagem do compose de desenvolvimento; um build de produção usaria `api.txt`.

- [ ] **Step 3: Adicionar o serviço `postgres-test` ao `docker-compose.yml`**

Inserir como primeiro serviço, antes de `redis`:

```yaml
  postgres-test:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: smartscout
      POSTGRES_PASSWORD: smartscout
      POSTGRES_DB: smartscout_test
    tmpfs:
      - /var/lib/postgresql/data
    ports:
      - "5433:5432"
```

`tmpfs` mantém o banco em memória: some a cada restart e é rápido, que é exatamente o que
se quer de um banco de teste.

- [ ] **Step 4: Dar ao serviço `api` a URL do banco de teste**

No serviço `api`, dentro de `environment`, acrescentar abaixo de `REDIS_URL`:

```yaml
      - TEST_DATABASE_URL=postgresql://smartscout:smartscout@postgres-test:5432/smartscout_test
```

- [ ] **Step 5: Subir e verificar**

```bash
docker compose up -d --build postgres-test api
docker compose exec api python -c "import pytest, httpx; print(pytest.__version__, httpx.__version__)"
```

Esperado: `8.4.2 0.28.1`

```bash
docker compose exec api python -c "import os; print(os.environ['TEST_DATABASE_URL'])"
```

Esperado: a URL apontando para `postgres-test`.

- [ ] **Step 6: Commit**

```bash
git add backend/requirements/dev.txt backend/Dockerfile docker-compose.yml
git commit -m "chore(tests): adiciona postgres-test no compose e deps de teste"
```

---

### Task 2: Fixtures do pytest com schema vindo das migrações

**Files:**
- Create: `backend/pytest.ini`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/integration/__init__.py`
- Create: `backend/tests/unit/__init__.py`
- Test: `backend/tests/integration/test_migrations.py`

- [ ] **Step 1: Criar `backend/pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v
```

- [ ] **Step 2: Criar os pacotes de teste**

Criar três arquivos vazios: `backend/tests/__init__.py`, `backend/tests/unit/__init__.py`
e `backend/tests/integration/__init__.py`.

- [ ] **Step 3: Escrever o teste que falha**

`backend/tests/integration/test_migrations.py`:

```python
"""
Prova que o schema de teste nasce das migracoes Alembic, e nao de create_all.
Se este teste passar, toda a suite esta exercitando as migracoes (P5 da spec).
"""
from sqlalchemy import text


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
```

- [ ] **Step 4: Rodar e verificar que falha**

```bash
docker compose exec api pytest tests/integration/test_migrations.py -v
```

Esperado: FAIL com `fixture 'engine' not found`.

- [ ] **Step 5: Escrever o `conftest.py`**

`backend/tests/conftest.py`:

```python
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
```

- [ ] **Step 6: Rodar e verificar que passa**

```bash
docker compose exec api pytest tests/integration/test_migrations.py -v
```

Esperado: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/pytest.ini backend/tests/
git commit -m "test: monta a suite com schema vindo das migracoes alembic"
```

---

### Task 3: Consolidacao das duas arvores de teste

A Task 3 original escrevia testes de caracterizacao de `register`/`login`. Foi substituida:
esses testes **ja existem** em `tests/unit/backend/test_auth.py` (14 casos). O trabalho real
e consolidar as duas arvores antes que mais testes sejam escritos na errada.

**Files:**
- Move: `tests/unit/backend/*.py` -> `backend/tests/`
- Modify: `pytest.ini` (raiz)
- Modify: `backend/tests/integration/conftest.py`
- Modify: `docs/F0-reestruturacao-explicado.md`

- [ ] **Step 1: Mover os testes de backend**

Mover `test_auth.py`, `test_exceptions.py`, `test_jobs.py`, `test_storage.py` e
`test_tasks.py` de `tests/unit/backend/` para `backend/tests/`, distribuindo entre
`unit/` e `integration/` conforme cada um precise ou nao de banco. Descartar
`tests/unit/backend/conftest.py` (SQLite + create_all) -- as fixtures equivalentes ja
existem em `backend/tests/integration/conftest.py`.

- [ ] **Step 2: Reescopar o pytest.ini da raiz**

```ini
[pytest]
testpaths = tests/unit/ml tests/integration
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v
```

- [ ] **Step 3: Corrigir a guarda para cobrir tambem o subprocesso do Alembic**

A guarda valida `app_engine.url`, mas `alembic upgrade head` roda num subprocesso que
resolve a propria URL em `backend/alembic/env.py:31`. Hoje so e seguro porque
`load_dotenv` usa `override=False`. Passar a URL explicitamente ao subprocesso, em vez
de depender dessa semantica.

- [ ] **Step 4: Dar sessao propria a cada requisicao no fixture `client`**

Hoje `client` injeta a mesma `Session` do teste no handler, entao um endpoint que
esquece de commitar passa mesmo assim, e um erro de transacao contamina as assercoes
seguintes. Trocar por uma sessao nova por requisicao.

- [ ] **Step 5: Atualizar a documentacao**

`docs/F0-reestruturacao-explicado.md:225` manda rodar `../tests/unit/backend`, que deixa
de existir. Documentar o comando real: `docker compose exec api pytest`.

- [ ] **Step 6: Verificar**

```bash
docker compose exec api pytest -v
```

Esperado: os 33 testes migrados mais os 7 da infra, todos verdes contra Postgres com
schema vindo das migracoes.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "test: consolida as suites de backend em backend/tests"
```

---

## Bloco B — Migração 1: `role`

### Task 4: Campo `role` em `users`

**Files:**
- Modify: `backend/app/modules/identity/models.py`
- Create: `backend/alembic/versions/<gerado>_adiciona_role_em_users.py`
- Test: `backend/tests/integration/test_migrations.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar ao final de `backend/tests/integration/test_migrations.py`:

```python
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


def test_usuario_existente_recebe_role_athlete_no_backfill(engine):
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
```

- [ ] **Step 2: Rodar e verificar que falha**

```bash
docker compose exec api pytest tests/integration/test_migrations.py -v
```

Esperado: FAIL — `coluna role nao existe em users` e `ImportError: cannot import name 'UserRole'`.

- [ ] **Step 3: Adicionar o enum e o campo ao modelo**

Em `backend/app/modules/identity/models.py`, acrescentar o import de `Enum` no topo e o
enum antes da classe `User`:

```python
from enum import Enum
```

```python
class UserRole(str, Enum):
    """Papel do usuario. Definido no cadastro e imutavel (secao 13 da spec de origem)."""

    ATHLETE = "ATHLETE"
    SCOUT = "SCOUT"
    CLUB = "CLUB"
```

E dentro de `class User`, logo abaixo de `last_name`:

```python
    role: UserRole = Field(default=UserRole.ATHLETE)
```

- [ ] **Step 4: Gerar a migração**

```bash
docker compose exec api alembic revision -m "adiciona role em users"
```

- [ ] **Step 5: Escrever o corpo da migração**

No arquivo gerado em `backend/alembic/versions/`, manter o `revision` que o Alembic criou
e preencher o resto:

```python
down_revision = "dc5867a2d8e8"

import sqlalchemy as sa
from alembic import op

user_role = sa.Enum("ATHLETE", "SCOUT", "CLUB", name="userrole")


def upgrade() -> None:
    user_role.create(op.get_bind(), checkfirst=True)
    # Nullable primeiro para nao quebrar as linhas existentes.
    op.add_column("users", sa.Column("role", user_role, nullable=True))
    op.execute("UPDATE users SET role = 'ATHLETE' WHERE role IS NULL")
    op.alter_column("users", "role", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "role")
    user_role.drop(op.get_bind(), checkfirst=True)
```

Adicionar a coluna já como `NOT NULL` falharia em qualquer base com usuários; por isso os
três passos.

- [ ] **Step 6: Rodar e verificar que passa**

```bash
docker compose exec api pytest tests/integration/test_migrations.py -v
```

Esperado: 4 passed.

- [ ] **Step 7: Verificar que a migração é reversível**

```bash
docker compose exec api alembic -x db_url=postgresql://smartscout:smartscout@postgres-test:5432/smartscout_test downgrade -1 && \n  docker compose exec api alembic -x db_url=postgresql://smartscout:smartscout@postgres-test:5432/smartscout_test upgrade head
```

Esperado: ambos terminam sem erro.

- [ ] **Step 8: Commit**

```bash
git add backend/app/modules/identity/models.py backend/alembic/versions/ backend/tests/
git commit -m "feat(identity): adiciona role em users com backfill"
```

---

### Task 5: `register` aceita `role` e rejeita papéis sem perfil

**Files:**
- Modify: `backend/app/modules/identity/schemas.py`
- Modify: `backend/app/modules/identity/router.py`
- Test: `backend/tests/integration/test_auth_caracterizacao.py`

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar ao final de `backend/tests/integration/test_auth_caracterizacao.py`:

```python
def test_register_sem_role_assume_athlete(client):
    resposta = client.post("/api/v1/auth/register", json=PAYLOAD)

    assert resposta.json()["user"]["role"] == "ATHLETE"


def test_register_com_role_athlete(client):
    resposta = client.post(
        "/api/v1/auth/register", json={**PAYLOAD, "role": "ATHLETE"}
    )

    assert resposta.status_code == 200
    assert resposta.json()["user"]["role"] == "ATHLETE"


def test_register_com_role_scout_e_rejeitado(client):
    resposta = client.post("/api/v1/auth/register", json={**PAYLOAD, "role": "SCOUT"})

    assert resposta.status_code == 422
    assert "ATHLETE" in resposta.json()["detail"]


def test_register_com_role_club_e_rejeitado(client):
    resposta = client.post("/api/v1/auth/register", json={**PAYLOAD, "role": "CLUB"})

    assert resposta.status_code == 422
```

- [ ] **Step 2: Rodar e verificar que falham**

```bash
docker compose exec api pytest tests/integration/test_auth_caracterizacao.py -v
```

Esperado: FAIL — `KeyError: 'role'` nos dois primeiros e 200 em vez de 422 nos outros.

- [ ] **Step 3: Adicionar `role` aos schemas**

Em `backend/app/modules/identity/schemas.py`, acrescentar o import e os campos:

```python
from app.modules.identity.models import UserRole
```

Em `UserCreate`, abaixo de `last_name`:

```python
    role: UserRole = UserRole.ATHLETE
```

Em `UserResponse`, abaixo de `last_name`:

```python
    role: UserRole
```

- [ ] **Step 4: Validar o papel no router**

Em `backend/app/modules/identity/router.py`, acrescentar aos imports:

```python
from app.core.exceptions import ValidationError
from app.modules.identity.models import UserRole
```

Dentro de `register`, como primeira instrução do corpo:

```python
    if data.role is not UserRole.ATHLETE:
        raise ValidationError(
            "Nesta versao apenas o papel ATHLETE pode ser cadastrado."
        )
```

Passar `role` na construção do `User`:

```python
    user = User(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        role=data.role,
    )
```

E incluir `role` nos dois `UserResponse(...)` do arquivo (em `register` e em `login`):

```python
            role=user.role,
```

- [ ] **Step 5: Rodar e verificar que passam**

```bash
docker compose exec api pytest tests/integration/test_auth_caracterizacao.py -v
```

Esperado: 9 passed. Os cinco testes de caracterização originais continuam verdes — é isso
que prova que a mudança não regrediu o fluxo.

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/identity/ backend/tests/
git commit -m "feat(identity): register aceita role e rejeita papeis sem perfil"
```

---

## Bloco C — Migração 2 e módulo `profiles`

### Task 6: Modelo e migração de `athlete_profiles`

**Files:**
- Create: `backend/app/modules/profiles/__init__.py`
- Create: `backend/app/modules/profiles/models.py`
- Modify: `backend/alembic/env.py:24`
- Create: `backend/alembic/versions/<gerado>_cria_athlete_profiles.py`
- Test: `backend/tests/integration/test_migrations.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar ao final de `backend/tests/integration/test_migrations.py`:

```python
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


def test_backfill_cria_perfil_para_usuario_existente(engine):
    from sqlmodel import Session, select
    from app.modules.profiles.models import AthleteProfile

    with Session(engine) as s:
        perfis = s.exec(select(AthleteProfile)).all()

    assert isinstance(perfis, list)
```

- [ ] **Step 2: Rodar e verificar que falha**

```bash
docker compose exec api pytest tests/integration/test_migrations.py -v
```

Esperado: FAIL — `tabela athlete_profiles nao existe`.

- [ ] **Step 3: Criar o pacote e o modelo**

`backend/app/modules/profiles/__init__.py`:

```python
"""Modulo de perfis por papel."""
```

`backend/app/modules/profiles/models.py`:

```python
import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class Position(str, Enum):
    GOLEIRO = "GOLEIRO"
    ZAGUEIRO = "ZAGUEIRO"
    LATERAL = "LATERAL"
    VOLANTE = "VOLANTE"
    MEIA = "MEIA"
    ATACANTE = "ATACANTE"


class DominantFoot(str, Enum):
    DESTRO = "DESTRO"
    CANHOTO = "CANHOTO"
    AMBIDESTRO = "AMBIDESTRO"


class AthleteStatus(str, Enum):
    DISPONIVEL = "DISPONIVEL"
    CONTRATADO = "CONTRATADO"
    NAO_DISPONIVEL = "NAO_DISPONIVEL"


class AthleteProfile(SQLModel, table=True):
    """Perfil 1:1 do usuario com papel ATHLETE."""

    __tablename__ = "athlete_profiles"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    position: Optional[Position] = Field(default=None, index=True)
    birth_date: Optional[date] = Field(default=None, index=True)
    height_cm: Optional[int] = None
    dominant_foot: Optional[DominantFoot] = None
    state: Optional[str] = Field(default=None, max_length=2, index=True)
    city: Optional[str] = None
    current_club: Optional[str] = None
    bio: Optional[str] = None
    avatar_path: Optional[str] = None
    status: AthleteStatus = Field(default=AthleteStatus.DISPONIVEL)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

Idade não é coluna: sai de `birth_date` na leitura (§4.5 da spec).

- [ ] **Step 4: Registrar o modelo no Alembic**

Em `backend/alembic/env.py`, abaixo da linha `import app.modules.clips.models  # noqa: F401,E402`:

```python
import app.modules.profiles.models  # noqa: F401,E402
```

Sem isso o autogenerate não enxerga a tabela.

- [ ] **Step 5: Gerar a migração**

```bash
docker compose exec api alembic revision -m "cria athlete_profiles"
```

- [ ] **Step 6: Escrever o corpo da migração**

No arquivo gerado, `down_revision` recebe o `revision` da migração da Task 4:

```python
import sqlalchemy as sa
import sqlmodel
from alembic import op

# ATENCAO: o tipo nativo NAO pode se chamar "position" -- POSITION e palavra reservada
# do Postgres em posicao de nome de tipo, e `CREATE TABLE t (p position)` da erro de
# sintaxe. A classe Python continua `Position`; so o nome do tipo no banco muda.
position = sa.Enum(
    "GOLEIRO", "ZAGUEIRO", "LATERAL", "VOLANTE", "MEIA", "ATACANTE",
    name="athleteposition",
)
dominant_foot = sa.Enum("DESTRO", "CANHOTO", "AMBIDESTRO", name="dominantfoot")
athlete_status = sa.Enum(
    "DISPONIVEL", "CONTRATADO", "NAO_DISPONIVEL", name="athletestatus"
)


def upgrade() -> None:
    # Nao chamar enum.create() aqui: op.create_table despacha before_create com
    # checkfirst=False, entao os tipos ja nascem com o CREATE TABLE. Um create previo
    # falharia com "type already exists". O downgrade, esse sim, precisa dropar os tres.
    op.create_table(
        "athlete_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("position", position, nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("dominant_foot", dominant_foot, nullable=True),
        sa.Column("state", sqlmodel.sql.sqltypes.AutoString(length=2), nullable=True),
        sa.Column("city", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("current_club", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("bio", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("avatar_path", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("status", athlete_status, nullable=False, server_default="DISPONIVEL"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_athlete_profiles_position", "athlete_profiles", ["position"])
    op.create_index("ix_athlete_profiles_birth_date", "athlete_profiles", ["birth_date"])
    op.create_index("ix_athlete_profiles_state", "athlete_profiles", ["state"])
    op.create_index(
        "ix_athlete_profiles_position_state", "athlete_profiles", ["position", "state"]
    )

    # Backfill: todo usuario ATHLETE precisa de perfil (secao 5.1 da spec de origem).
    op.execute(
        """
        INSERT INTO athlete_profiles (user_id, status, created_at, updated_at)
        SELECT id, 'DISPONIVEL', NOW(), NOW() FROM users WHERE role = 'ATHLETE'
        ON CONFLICT (user_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_athlete_profiles_position_state", "athlete_profiles")
    op.drop_index("ix_athlete_profiles_birth_date", "athlete_profiles")
    op.drop_index("ix_athlete_profiles_position", "athlete_profiles")
    op.drop_table("athlete_profiles")

    bind = op.get_bind()
    athlete_status.drop(bind, checkfirst=True)
    dominant_foot.drop(bind, checkfirst=True)
    position.drop(bind, checkfirst=True)
```

O `ON CONFLICT DO NOTHING` torna o backfill idempotente (risco PR5 da spec).

- [ ] **Step 7: Rodar e verificar que passa**

```bash
docker compose exec api pytest tests/integration/test_migrations.py -v
```

Esperado: 6 passed.

- [ ] **Step 8: Verificar reversibilidade**

```bash
docker compose exec api alembic -x db_url=postgresql://smartscout:smartscout@postgres-test:5432/smartscout_test downgrade -1 && \n  docker compose exec api alembic -x db_url=postgresql://smartscout:smartscout@postgres-test:5432/smartscout_test upgrade head
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/modules/profiles/ backend/alembic/ backend/tests/
git commit -m "feat(profiles): cria athlete_profiles com backfill idempotente"
```

---

### Task 7: Repository de perfis

**Files:**
- Create: `backend/app/modules/profiles/repository.py`

- [ ] **Step 1: Escrever o repository**

Não há teste unitário próprio: o repository é exercitado pelos testes de integração das
Tasks 9 e 10. O que ele existe para permitir é testar o **service** sem banco.

`backend/app/modules/profiles/repository.py`:

```python
"""
Acesso a dados de perfis. Consumido apenas pelo proprio modulo.

`AthleteProfileRecord` existe para que o service nunca receba um objeto ORM: e o que
permite substituir esta implementacao por uma fake em dicionario nos testes unitarios.
"""
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Optional, Protocol

from sqlmodel import Session, func, select

from app.modules.clips.models import Clip, ProcessingJob, Video
from app.modules.identity.models import User, UserRole
from app.modules.profiles.models import (
    AthleteProfile,
    AthleteStatus,
    DominantFoot,
    Position,
)


@dataclass(frozen=True)
class AthleteProfileRecord:
    """Perfil do atleta somado aos dados de identidade, sem acoplamento com ORM."""

    user_id: uuid.UUID
    first_name: str
    last_name: str
    position: Optional[Position]
    birth_date: Optional[date]
    height_cm: Optional[int]
    dominant_foot: Optional[DominantFoot]
    state: Optional[str]
    city: Optional[str]
    current_club: Optional[str]
    bio: Optional[str]
    avatar_path: Optional[str]
    status: AthleteStatus


class AthleteProfileRepository(Protocol):
    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[AthleteProfileRecord]: ...

    def count_clips(self, user_id: uuid.UUID) -> int: ...

    def update(
        self, user_id: uuid.UUID, changes: dict[str, Any]
    ) -> Optional[AthleteProfileRecord]: ...


class SqlAthleteProfileRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[AthleteProfileRecord]:
        linha = self.session.exec(
            select(User, AthleteProfile)
            .join(AthleteProfile, AthleteProfile.user_id == User.id)
            .where(User.id == user_id)
            .where(User.role == UserRole.ATHLETE)
        ).first()

        if linha is None:
            return None

        user, perfil = linha
        return self._to_record(user, perfil)

    def count_clips(self, user_id: uuid.UUID) -> int:
        total = self.session.exec(
            select(func.count(Clip.id))
            .join(ProcessingJob, Clip.job_id == ProcessingJob.id)
            .join(Video, ProcessingJob.video_id == Video.id)
            .where(Video.user_id == user_id)
        ).one()
        return int(total)

    def update(
        self, user_id: uuid.UUID, changes: dict[str, Any]
    ) -> Optional[AthleteProfileRecord]:
        perfil = self.session.get(AthleteProfile, user_id)
        if perfil is None:
            return None

        for campo, valor in changes.items():
            setattr(perfil, campo, valor)
        perfil.updated_at = datetime.now(timezone.utc)

        self.session.add(perfil)
        self.session.commit()
        self.session.refresh(perfil)

        user = self.session.get(User, user_id)
        return self._to_record(user, perfil)

    @staticmethod
    def _to_record(user: User, perfil: AthleteProfile) -> AthleteProfileRecord:
        return AthleteProfileRecord(
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            position=perfil.position,
            birth_date=perfil.birth_date,
            height_cm=perfil.height_cm,
            dominant_foot=perfil.dominant_foot,
            state=perfil.state,
            city=perfil.city,
            current_club=perfil.current_club,
            bio=perfil.bio,
            avatar_path=perfil.avatar_path,
            status=perfil.status,
        )
```

- [ ] **Step 2: Verificar que o módulo importa**

```bash
docker compose exec api python -c "from app.modules.profiles.repository import SqlAthleteProfileRepository; print('ok')"
```

Esperado: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/modules/profiles/repository.py
git commit -m "feat(profiles): adiciona repository com record desacoplado do orm"
```

---

### Task 8: Service de perfis com repository fake

**Files:**
- Create: `backend/app/modules/profiles/service.py`
- Test: `backend/tests/unit/test_profiles_service.py`

- [ ] **Step 1: Escrever os testes que falham**

`backend/tests/unit/test_profiles_service.py`:

```python
"""
Testes unitarios do service: sem banco, sem HTTP. O repository e uma fake em dicionario.
Este e o loop rapido do TDD -- roda em milissegundos.
"""
import uuid
from datetime import date
from typing import Any, Optional

import pytest

from app.core.exceptions import NotFoundError
from app.modules.profiles.models import AthleteStatus, DominantFoot, Position
from app.modules.profiles.repository import AthleteProfileRecord
from app.modules.profiles.service import ProfilesService

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def um_record(**overrides: Any) -> AthleteProfileRecord:
    base = dict(
        user_id=USER_ID,
        first_name="Jeh",
        last_name="Rodrigues",
        position=Position.ATACANTE,
        birth_date=date(2007, 3, 10),
        height_cm=178,
        dominant_foot=DominantFoot.DESTRO,
        state="SP",
        city="Campinas",
        current_club=None,
        bio=None,
        avatar_path=None,
        status=AthleteStatus.DISPONIVEL,
    )
    base.update(overrides)
    return AthleteProfileRecord(**base)


class FakeRepository:
    def __init__(self, record: Optional[AthleteProfileRecord] = None, clips: int = 0):
        self.record = record
        self.clips = clips
        self.ultima_atualizacao: Optional[dict[str, Any]] = None

    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[AthleteProfileRecord]:
        if self.record is None or self.record.user_id != user_id:
            return None
        return self.record

    def count_clips(self, user_id: uuid.UUID) -> int:
        return self.clips

    def update(
        self, user_id: uuid.UUID, changes: dict[str, Any]
    ) -> Optional[AthleteProfileRecord]:
        if self.record is None:
            return None
        self.ultima_atualizacao = changes
        self.record = um_record(**changes)
        return self.record


def test_calcula_idade_a_partir_da_data_de_nascimento():
    service = ProfilesService(
        FakeRepository(um_record(birth_date=date(2007, 3, 10))),
        hoje=lambda: date(2026, 9, 2),
    )

    assert service.get_athlete_profile(USER_ID).age == 19


def test_idade_desconta_aniversario_ainda_nao_ocorrido_no_ano():
    service = ProfilesService(
        FakeRepository(um_record(birth_date=date(2007, 12, 31))),
        hoje=lambda: date(2026, 9, 2),
    )

    assert service.get_athlete_profile(USER_ID).age == 18


def test_idade_no_proprio_dia_do_aniversario():
    service = ProfilesService(
        FakeRepository(um_record(birth_date=date(2007, 9, 2))),
        hoje=lambda: date(2026, 9, 2),
    )

    assert service.get_athlete_profile(USER_ID).age == 19


def test_sem_data_de_nascimento_a_idade_e_nula():
    service = ProfilesService(
        FakeRepository(um_record(birth_date=None)), hoje=lambda: date(2026, 9, 2)
    )

    assert service.get_athlete_profile(USER_ID).age is None


def test_perfil_inexistente_levanta_not_found():
    service = ProfilesService(FakeRepository(None), hoje=lambda: date(2026, 9, 2))

    with pytest.raises(NotFoundError):
        service.get_athlete_profile(USER_ID)


def test_inclui_a_contagem_de_clipes():
    service = ProfilesService(
        FakeRepository(um_record(), clips=42), hoje=lambda: date(2026, 9, 2)
    )

    assert service.get_athlete_profile(USER_ID).clips_count == 42


def test_atualizacao_parcial_so_repassa_os_campos_enviados():
    repo = FakeRepository(um_record())
    service = ProfilesService(repo, hoje=lambda: date(2026, 9, 2))

    service.update_athlete_profile(USER_ID, {"city": "Santos"})

    assert repo.ultima_atualizacao == {"city": "Santos"}


def test_atualizar_perfil_inexistente_levanta_not_found():
    service = ProfilesService(FakeRepository(None), hoje=lambda: date(2026, 9, 2))

    with pytest.raises(NotFoundError):
        service.update_athlete_profile(USER_ID, {"city": "Santos"})
```

- [ ] **Step 2: Rodar e verificar que falham**

```bash
docker compose exec api pytest tests/unit/test_profiles_service.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'app.modules.profiles.service'`.

- [ ] **Step 3: Escrever o service**

`backend/app/modules/profiles/service.py`:

```python
"""
Regra de negocio de perfis. Unico ponto de entrada para outros modulos (regra D3).
Nao conhece HTTP nem sessao de banco.
"""
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Optional

from app.core.exceptions import NotFoundError
from app.modules.profiles.models import AthleteStatus, DominantFoot, Position
from app.modules.profiles.repository import AthleteProfileRecord, AthleteProfileRepository


@dataclass(frozen=True)
class AthleteProfileView:
    """O que o mundo externo enxerga de um perfil, com a idade ja derivada."""

    user_id: uuid.UUID
    first_name: str
    last_name: str
    position: Optional[Position]
    age: Optional[int]
    height_cm: Optional[int]
    dominant_foot: Optional[DominantFoot]
    state: Optional[str]
    city: Optional[str]
    current_club: Optional[str]
    bio: Optional[str]
    avatar_path: Optional[str]
    status: AthleteStatus
    clips_count: int


def calcular_idade(nascimento: date, hoje: date) -> int:
    """Idade em anos completos."""
    aniversario_passou = (hoje.month, hoje.day) >= (nascimento.month, nascimento.day)
    return hoje.year - nascimento.year - (0 if aniversario_passou else 1)


class ProfilesService:
    def __init__(
        self,
        repository: AthleteProfileRepository,
        hoje: Callable[[], date] = date.today,
    ):
        self.repository = repository
        self.hoje = hoje

    def get_athlete_profile(self, user_id: uuid.UUID) -> AthleteProfileView:
        record = self.repository.get_by_user_id(user_id)
        if record is None:
            raise NotFoundError("Atleta nao encontrado.")

        return self._to_view(record, self.repository.count_clips(user_id))

    def update_athlete_profile(
        self, user_id: uuid.UUID, changes: dict[str, Any]
    ) -> AthleteProfileView:
        record = self.repository.update(user_id, changes)
        if record is None:
            raise NotFoundError("Atleta nao encontrado.")

        return self._to_view(record, self.repository.count_clips(user_id))

    def _to_view(self, record: AthleteProfileRecord, clips_count: int) -> AthleteProfileView:
        idade = (
            calcular_idade(record.birth_date, self.hoje())
            if record.birth_date is not None
            else None
        )
        return AthleteProfileView(
            user_id=record.user_id,
            first_name=record.first_name,
            last_name=record.last_name,
            position=record.position,
            age=idade,
            height_cm=record.height_cm,
            dominant_foot=record.dominant_foot,
            state=record.state,
            city=record.city,
            current_club=record.current_club,
            bio=record.bio,
            avatar_path=record.avatar_path,
            status=record.status,
            clips_count=clips_count,
        )
```

- [ ] **Step 4: Rodar e verificar que passam**

```bash
docker compose exec api pytest tests/unit/test_profiles_service.py -v
```

Esperado: 8 passed, em menos de um segundo — sem banco.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/profiles/service.py backend/tests/unit/
git commit -m "feat(profiles): service com idade derivada e erros de dominio"
```

---

### Task 9: Rota `GET /profiles/athletes/{user_id}`

**Files:**
- Create: `backend/app/modules/profiles/schemas.py`
- Create: `backend/app/modules/profiles/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/integration/test_profiles_router.py`

- [ ] **Step 1: Escrever os testes que falham**

`backend/tests/integration/test_profiles_router.py`:

```python
"""Testes de integracao das rotas de perfil: TestClient contra o banco de teste."""
import uuid
from datetime import date

import pytest

from app.modules.profiles.models import AthleteProfile, AthleteStatus, DominantFoot, Position


@pytest.fixture
def perfil(session, usuario) -> AthleteProfile:
    p = AthleteProfile(
        user_id=usuario.id,
        position=Position.ATACANTE,
        birth_date=date(2007, 3, 10),
        height_cm=178,
        dominant_foot=DominantFoot.DESTRO,
        state="SP",
        city="Campinas",
        bio="Atleta de base.",
        status=AthleteStatus.DISPONIVEL,
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def test_sem_jwt_devolve_401(client, usuario):
    resposta = client.get(f"/api/v1/profiles/athletes/{usuario.id}")

    assert resposta.status_code == 401


def test_devolve_o_perfil_do_atleta(client, auth_headers, usuario, perfil):
    resposta = client.get(
        f"/api/v1/profiles/athletes/{usuario.id}", headers=auth_headers
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["first_name"] == "Jeh"
    assert corpo["last_name"] == "Rodrigues"
    assert corpo["position"] == "ATACANTE"
    assert corpo["height_cm"] == 178
    assert corpo["city"] == "Campinas"
    assert corpo["state"] == "SP"
    assert corpo["status"] == "DISPONIVEL"
    assert corpo["clips_count"] == 0
    assert isinstance(corpo["age"], int)


def test_campos_sociais_nao_estao_no_contrato_da_fatia_1(client, auth_headers, usuario, perfil):
    corpo = client.get(
        f"/api/v1/profiles/athletes/{usuario.id}", headers=auth_headers
    ).json()

    assert "is_followed_by_me" not in corpo
    assert "is_saved_by_me" not in corpo


def test_id_inexistente_devolve_404(client, auth_headers):
    resposta = client.get(
        f"/api/v1/profiles/athletes/{uuid.uuid4()}", headers=auth_headers
    )

    assert resposta.status_code == 404


def test_usuario_sem_perfil_de_atleta_devolve_404(client, auth_headers, usuario):
    resposta = client.get(
        f"/api/v1/profiles/athletes/{usuario.id}", headers=auth_headers
    )

    assert resposta.status_code == 404
```

No FastAPI 0.133.1 instalado, header `Authorization` ausente devolve **401**
(`{"detail": "Not authenticated"}`), nao 403. Versoes antigas devolviam 403, razao pela qual
`test_auth.py:190` e `test_jobs.py:86` hedgeiam com `in (401, 403)`.

- [ ] **Step 2: Rodar e verificar que falham**

```bash
docker compose exec api pytest tests/integration/test_profiles_router.py -v
```

Esperado: FAIL com 404 em todas as rotas — o router ainda não existe.

- [ ] **Step 3: Escrever os schemas**

`backend/app/modules/profiles/schemas.py`:

```python
"""DTOs de entrada e saida do modulo de perfis."""
import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.profiles.models import AthleteStatus, DominantFoot, Position


class AthleteProfileResponse(BaseModel):
    """Perfil do atleta como sai na API. `age` ja vem derivada de birth_date."""

    user_id: uuid.UUID
    first_name: str
    last_name: str
    position: Optional[Position]
    status: AthleteStatus
    age: Optional[int]
    height_cm: Optional[int]
    dominant_foot: Optional[DominantFoot]
    city: Optional[str]
    state: Optional[str]
    current_club: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    clips_count: int


class AthleteProfileUpdate(BaseModel):
    """Atualizacao parcial: apenas os campos enviados sao alterados."""

    position: Optional[Position] = None
    birth_date: Optional[date] = None
    height_cm: Optional[int] = Field(default=None, ge=100, le=250)
    dominant_foot: Optional[DominantFoot] = None
    state: Optional[str] = Field(default=None, min_length=2, max_length=2)
    city: Optional[str] = None
    current_club: Optional[str] = None
    bio: Optional[str] = None
    status: Optional[AthleteStatus] = None
```

- [ ] **Step 4: Escrever o router**

`backend/app/modules/profiles/router.py`:

```python
"""
HTTP do modulo de perfis: rota, validacao e serializacao. Sem regra de negocio.
Erros sobem como excecao de dominio e sao traduzidos pelo handler unico do main.py.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.modules.identity.models import User
from app.modules.profiles.repository import SqlAthleteProfileRepository
from app.modules.profiles.schemas import AthleteProfileResponse
from app.modules.profiles.service import AthleteProfileView, ProfilesService

router = APIRouter(prefix="/profiles", tags=["profiles"])


def get_service(session: Session = Depends(get_session)) -> ProfilesService:
    return ProfilesService(SqlAthleteProfileRepository(session))


def _to_response(view: AthleteProfileView) -> AthleteProfileResponse:
    return AthleteProfileResponse(
        user_id=view.user_id,
        first_name=view.first_name,
        last_name=view.last_name,
        position=view.position,
        status=view.status,
        age=view.age,
        height_cm=view.height_cm,
        dominant_foot=view.dominant_foot,
        city=view.city,
        state=view.state,
        current_club=view.current_club,
        bio=view.bio,
        avatar_url=view.avatar_path,
        clips_count=view.clips_count,
    )


@router.get("/athletes/{user_id}", response_model=AthleteProfileResponse)
def get_athlete_profile(
    user_id: uuid.UUID,
    service: ProfilesService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Perfil de um atleta. Exige autenticacao (decisao P2 da spec)."""
    return _to_response(service.get_athlete_profile(user_id))
```

- [ ] **Step 5: Montar o router no `main.py`**

Em `backend/app/main.py`, acrescentar aos imports:

```python
from app.modules.profiles.router import router as profiles_router
```

E abaixo de `app.include_router(clips_router, prefix="/api/v1")`:

```python
app.include_router(profiles_router, prefix="/api/v1")
```

- [ ] **Step 6: Rodar e verificar que passam**

```bash
docker compose exec api pytest tests/integration/test_profiles_router.py -v
```

Esperado: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/modules/profiles/ backend/app/main.py backend/tests/
git commit -m "feat(profiles): expoe GET /profiles/athletes/{user_id}"
```

---

### Task 10: Rotas `GET /profiles/me` e `PUT /profiles/me`

**Files:**
- Modify: `backend/app/modules/profiles/router.py`
- Test: `backend/tests/integration/test_profiles_router.py`

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar ao final de `backend/tests/integration/test_profiles_router.py`:

```python
def test_me_devolve_o_proprio_perfil(client, auth_headers, perfil):
    resposta = client.get("/api/v1/profiles/me", headers=auth_headers)

    assert resposta.status_code == 200
    assert resposta.json()["city"] == "Campinas"


def test_put_me_atualiza_apenas_os_campos_enviados(client, auth_headers, perfil):
    resposta = client.put(
        "/api/v1/profiles/me", headers=auth_headers, json={"city": "Santos"}
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["city"] == "Santos"
    assert corpo["state"] == "SP"
    assert corpo["height_cm"] == 178


def test_put_me_reflete_no_get_seguinte(client, auth_headers, usuario, perfil):
    client.put(
        "/api/v1/profiles/me", headers=auth_headers, json={"status": "CONTRATADO"}
    )

    corpo = client.get(
        f"/api/v1/profiles/athletes/{usuario.id}", headers=auth_headers
    ).json()

    assert corpo["status"] == "CONTRATADO"


def test_put_me_com_altura_invalida_devolve_422(client, auth_headers, perfil):
    resposta = client.put(
        "/api/v1/profiles/me", headers=auth_headers, json={"height_cm": 12}
    )

    assert resposta.status_code == 422
```

- [ ] **Step 2: Rodar e verificar que falham**

```bash
docker compose exec api pytest tests/integration/test_profiles_router.py -v
```

Esperado: FAIL com 404 nas rotas `/profiles/me`.

- [ ] **Step 3: Adicionar as rotas**

Em `backend/app/modules/profiles/router.py`, acrescentar `AthleteProfileUpdate` ao import
de schemas:

```python
from app.modules.profiles.schemas import AthleteProfileResponse, AthleteProfileUpdate
```

E ao final do arquivo:

```python
@router.get("/me", response_model=AthleteProfileResponse)
def get_my_profile(
    service: ProfilesService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Proprio perfil, usado para popular o formulario de edicao."""
    return _to_response(service.get_athlete_profile(current_user.id))


@router.put("/me", response_model=AthleteProfileResponse)
def update_my_profile(
    payload: AthleteProfileUpdate,
    service: ProfilesService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Atualizacao parcial: exclude_unset garante que campos ausentes nao sejam zerados."""
    changes = payload.model_dump(exclude_unset=True)
    return _to_response(service.update_athlete_profile(current_user.id, changes))
```

**Atenção à ordem das rotas:** `/me` precisa ser declarada depois de
`/athletes/{user_id}` mas nunca como `/{algo}` genérico — como os prefixos são distintos
(`/athletes/...` e `/me`), não há ambiguidade.

- [ ] **Step 4: Rodar e verificar que passam**

```bash
docker compose exec api pytest tests/integration/ -v
```

Esperado: 9 passed em `test_profiles_router.py`, e a suíte inteira verde.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/profiles/router.py backend/tests/
git commit -m "feat(profiles): adiciona GET e PUT de /profiles/me"
```

---

### Task 11: `register` cria o perfil na mesma transação

**Files:**
- Modify: `backend/app/modules/identity/router.py`
- Test: `backend/tests/integration/test_auth_caracterizacao.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar ao final de `backend/tests/integration/test_auth_caracterizacao.py`:

```python
def test_register_cria_o_perfil_de_atleta_junto(client, session):
    import uuid as _uuid
    from sqlmodel import select
    from app.modules.profiles.models import AthleteProfile

    corpo = client.post("/api/v1/auth/register", json=PAYLOAD).json()
    user_id = _uuid.UUID(corpo["user"]["id"])

    perfil = session.exec(
        select(AthleteProfile).where(AthleteProfile.user_id == user_id)
    ).first()

    assert perfil is not None, "usuario ATHLETE sem perfil e estado invalido"
    assert perfil.status.value == "DISPONIVEL"


def test_perfil_recem_criado_e_visivel_na_api(client):
    corpo = client.post("/api/v1/auth/register", json=PAYLOAD).json()
    headers = {"Authorization": f"Bearer {corpo['access_token']}"}

    resposta = client.get(f"/api/v1/profiles/athletes/{corpo['user']['id']}", headers=headers)

    assert resposta.status_code == 200
    assert resposta.json()["age"] is None
```

- [ ] **Step 2: Rodar e verificar que falha**

```bash
docker compose exec api pytest tests/integration/test_auth_caracterizacao.py -v
```

Esperado: FAIL — `usuario ATHLETE sem perfil e estado invalido`.

- [ ] **Step 3: Criar o perfil dentro do register**

Em `backend/app/modules/identity/router.py`, acrescentar ao import:

```python
from app.modules.profiles.models import AthleteProfile
```

Em `register`, substituir o bloco que hoje faz `session.add(user)` / `session.commit()` /
`session.refresh(user)` por:

```python
    session.add(user)
    session.flush()  # atribui user.id sem encerrar a transacao

    session.add(AthleteProfile(user_id=user.id))
    session.commit()
    session.refresh(user)
```

`flush` antes do `add` do perfil é o que garante que usuário e perfil nasçam na **mesma**
transação: se o perfil falhar, o usuário não é criado.

- [ ] **Step 4: Rodar e verificar que passam**

```bash
docker compose exec api pytest tests/integration/ -v
```

Esperado: toda a suíte de integração verde, 11 testes em `test_auth_caracterizacao.py`.

- [ ] **Step 5: Rodar a suíte completa**

```bash
docker compose exec api pytest -v
```

Esperado: todos passando, unit e integration.

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/identity/router.py backend/tests/
git commit -m "feat(identity): cria athlete_profile na mesma transacao do cadastro"
```

---

## Bloco D — Frontend

### Task 12: Vitest

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.js`
- Create: `frontend/src/test/setup.ts`

- [ ] **Step 1: Instalar as dependências**

```bash
docker compose exec web npm install --save @tanstack/react-query@5
docker compose exec web npm install --save-dev vitest@3 @testing-library/react@16 @testing-library/jest-dom@6 @testing-library/dom@10 jsdom@25
```

- [ ] **Step 2: Adicionar o script de teste**

Em `frontend/package.json`, dentro de `"scripts"`, acrescentar após `"lint"`:

```json
    "test": "vitest run",
    "test:watch": "vitest",
```

- [ ] **Step 3: Configurar o Vitest**

Substituir o conteúdo de `frontend/vite.config.js` por:

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
```

- [ ] **Step 4: Criar o setup**

`frontend/src/test/setup.ts`:

```ts
import '@testing-library/jest-dom/vitest';
```

- [ ] **Step 5: Escrever um teste de fumaça**

`frontend/src/test/setup.test.ts`:

```ts
import { describe, expect, it } from 'vitest';

describe('infra de testes', () => {
  it('roda e enxerga os matchers do jest-dom', () => {
    const el = document.createElement('div');
    el.textContent = 'ok';
    document.body.appendChild(el);

    expect(el).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Rodar e verificar que passa**

```bash
docker compose exec web npm test
```

Esperado: 1 passed.

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.js frontend/src/test/
git commit -m "chore(frontend): configura vitest e testing library"
```

---

### Task 13: `httpClient`

**Files:**
- Create: `frontend/src/shared/lib/httpClient.ts`
- Test: `frontend/src/shared/lib/httpClient.test.ts`

- [ ] **Step 1: Escrever os testes que falham**

`frontend/src/shared/lib/httpClient.test.ts`:

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, httpGet, httpPut } from './httpClient';

describe('httpClient', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'token-de-teste');
  });

  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('envia o JWT no header Authorization', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );

    await httpGet('/profiles/me');

    const headers = (fetchSpy.mock.calls[0][1]?.headers ?? {}) as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer token-de-teste');
  });

  it('devolve o corpo desserializado', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ city: 'Campinas' }), { status: 200 })
    );

    await expect(httpGet<{ city: string }>('/profiles/me')).resolves.toEqual({
      city: 'Campinas',
    });
  });

  it('lanca ApiError com o status em resposta de erro', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Atleta nao encontrado.' }), { status: 404 })
    );

    await expect(httpGet('/profiles/athletes/x')).rejects.toMatchObject({
      status: 404,
      message: 'Atleta nao encontrado.',
    });
  });

  it('ApiError expoe notFound para o 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'nao achou' }), { status: 404 })
    );

    const erro = await httpGet('/x').catch((e) => e as ApiError);

    expect(erro.notFound).toBe(true);
  });

  it('serializa o corpo no PUT', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({}), { status: 200 })
    );

    await httpPut('/profiles/me', { city: 'Santos' });

    expect(fetchSpy.mock.calls[0][1]?.body).toBe('{"city":"Santos"}');
  });
});
```

- [ ] **Step 2: Rodar e verificar que falham**

```bash
docker compose exec web npm test
```

Esperado: FAIL — `Failed to resolve import "./httpClient"`.

- [ ] **Step 3: Escrever o client**

`frontend/src/shared/lib/httpClient.ts`:

```ts
/**
 * Cliente HTTP do app: injeta o JWT, aplica timeout e converte erro em ApiError.
 * Primeira peca do F3; services/api.ts segue intacto ate a migracao daquele sub-projeto.
 */
const API_BASE = import.meta.env.VITE_API_PATH ?? 'http://127.0.0.1:8000/api/v1';
const REQUEST_TIMEOUT_MS = 15000;
const TOKEN_KEY = 'access_token';

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }

  get notFound(): boolean {
    return this.status === 404;
  }

  get unauthorized(): boolean {
    return this.status === 401 || this.status === 403;
  }
}

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: authHeaders(),
      signal: controller.signal,
    });

    if (!res.ok) {
      const corpo = await res.json().catch(() => ({}));
      throw new ApiError(res.status, corpo.detail ?? 'Erro inesperado na requisicao.');
    }

    if (res.status === 204) {
      return undefined as T;
    }

    return (await res.json()) as T;
  } finally {
    clearTimeout(timeoutId);
  }
}

export function httpGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'GET' });
}

export function httpPut<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'PUT', body: JSON.stringify(body) });
}
```

- [ ] **Step 4: Rodar e verificar que passam**

```bash
docker compose exec web npm test
```

Esperado: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shared/
git commit -m "feat(frontend): adiciona httpClient com jwt, timeout e erro tipado"
```

---

### Task 14: Mappers puros

**Files:**
- Create: `frontend/src/features/profiles/types.ts`
- Create: `frontend/src/features/profiles/mappers.ts`
- Test: `frontend/src/features/profiles/mappers.test.ts`

- [ ] **Step 1: Escrever os testes que falham**

`frontend/src/features/profiles/mappers.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { formatFoot, formatHeight, formatLocation, formatPosition, toAthleteProfileView } from './mappers';
import type { AthleteProfileDTO } from './types';

const DTO: AthleteProfileDTO = {
  user_id: 'abc',
  first_name: 'Jeh',
  last_name: 'Rodrigues',
  position: 'ATACANTE',
  status: 'DISPONIVEL',
  age: 19,
  height_cm: 178,
  dominant_foot: 'DESTRO',
  city: 'Campinas',
  state: 'SP',
  current_club: null,
  bio: null,
  avatar_url: null,
  clips_count: 42,
};

describe('formatHeight', () => {
  it('converte centimetros em metros', () => {
    expect(formatHeight(178)).toBe('1,78 m');
  });

  it('preenche o zero a esquerda nos centimetros', () => {
    expect(formatHeight(205)).toBe('2,05 m');
  });

  it('devolve travessao quando nao ha altura', () => {
    expect(formatHeight(null)).toBe('—');
  });
});

describe('formatLocation', () => {
  it('junta cidade e estado', () => {
    expect(formatLocation('Campinas', 'SP')).toBe('Campinas, SP');
  });

  it('usa so o que existe', () => {
    expect(formatLocation('Campinas', null)).toBe('Campinas');
    expect(formatLocation(null, 'SP')).toBe('SP');
  });

  it('devolve texto neutro quando nao ha nada', () => {
    expect(formatLocation(null, null)).toBe('Local nao informado');
  });
});

describe('formatPosition e formatFoot', () => {
  it('traduz a posicao para rotulo legivel', () => {
    expect(formatPosition('ATACANTE')).toBe('Atacante');
    expect(formatPosition('GOLEIRO')).toBe('Goleiro');
    expect(formatPosition(null)).toBe('Posicao nao informada');
  });

  it('traduz o pe dominante', () => {
    expect(formatFoot('DESTRO')).toBe('Destro');
    expect(formatFoot(null)).toBe('—');
  });
});

describe('toAthleteProfileView', () => {
  it('monta o view model a partir do DTO', () => {
    const view = toAthleteProfileView(DTO);

    expect(view.fullName).toBe('Jeh Rodrigues');
    expect(view.initial).toBe('J');
    expect(view.location).toBe('Campinas, SP');
    expect(view.heightLabel).toBe('1,78 m');
    expect(view.positionLabel).toBe('Atacante');
    expect(view.statusLabel).toBe('Disponivel para Clube');
    expect(view.ageLabel).toBe('19');
    expect(view.clipsCount).toBe(42);
  });

  it('usa travessao para idade ausente', () => {
    expect(toAthleteProfileView({ ...DTO, age: null }).ageLabel).toBe('—');
  });

  it('traduz os demais status', () => {
    expect(toAthleteProfileView({ ...DTO, status: 'CONTRATADO' }).statusLabel).toBe(
      'Contratado'
    );
    expect(toAthleteProfileView({ ...DTO, status: 'NAO_DISPONIVEL' }).statusLabel).toBe(
      'Nao disponivel'
    );
  });
});
```

- [ ] **Step 2: Rodar e verificar que falham**

```bash
docker compose exec web npm test
```

Esperado: FAIL — `Failed to resolve import "./mappers"`.

- [ ] **Step 3: Escrever os tipos**

`frontend/src/features/profiles/types.ts`:

```ts
export type Position =
  | 'GOLEIRO'
  | 'ZAGUEIRO'
  | 'LATERAL'
  | 'VOLANTE'
  | 'MEIA'
  | 'ATACANTE';

export type DominantFoot = 'DESTRO' | 'CANHOTO' | 'AMBIDESTRO';

export type AthleteStatus = 'DISPONIVEL' | 'CONTRATADO' | 'NAO_DISPONIVEL';

/** Resposta crua da API, em snake_case. */
export interface AthleteProfileDTO {
  user_id: string;
  first_name: string;
  last_name: string;
  position: Position | null;
  status: AthleteStatus;
  age: number | null;
  height_cm: number | null;
  dominant_foot: DominantFoot | null;
  city: string | null;
  state: string | null;
  current_club: string | null;
  bio: string | null;
  avatar_url: string | null;
  clips_count: number;
}

/** O que a tela consome: tudo ja formatado, sem logica no JSX. */
export interface AthleteProfileView {
  userId: string;
  fullName: string;
  initial: string;
  positionLabel: string;
  statusLabel: string;
  location: string;
  ageLabel: string;
  heightLabel: string;
  footLabel: string;
  currentClub: string | null;
  bio: string | null;
  avatarUrl: string | null;
  clipsCount: number;
}
```

- [ ] **Step 4: Escrever os mappers**

`frontend/src/features/profiles/mappers.ts`:

```ts
/**
 * Funcoes puras de formatacao. Ficam aqui, e nao no JSX, para poderem ser testadas
 * e para a pagina nao acumular regra de apresentacao espalhada.
 */
import type {
  AthleteProfileDTO,
  AthleteProfileView,
  AthleteStatus,
  DominantFoot,
  Position,
} from './types';

const SEM_VALOR = '—';

const ROTULO_POSICAO: Record<Position, string> = {
  GOLEIRO: 'Goleiro',
  ZAGUEIRO: 'Zagueiro',
  LATERAL: 'Lateral',
  VOLANTE: 'Volante',
  MEIA: 'Meia',
  ATACANTE: 'Atacante',
};

const ROTULO_PE: Record<DominantFoot, string> = {
  DESTRO: 'Destro',
  CANHOTO: 'Canhoto',
  AMBIDESTRO: 'Ambidestro',
};

const ROTULO_STATUS: Record<AthleteStatus, string> = {
  DISPONIVEL: 'Disponivel para Clube',
  CONTRATADO: 'Contratado',
  NAO_DISPONIVEL: 'Nao disponivel',
};

export function formatHeight(heightCm: number | null): string {
  if (heightCm === null) return SEM_VALOR;

  const metros = Math.floor(heightCm / 100);
  const centimetros = String(heightCm % 100).padStart(2, '0');
  return `${metros},${centimetros} m`;
}

export function formatLocation(city: string | null, state: string | null): string {
  const partes = [city, state].filter((p): p is string => Boolean(p));
  return partes.length > 0 ? partes.join(', ') : 'Local nao informado';
}

export function formatPosition(position: Position | null): string {
  return position ? ROTULO_POSICAO[position] : 'Posicao nao informada';
}

export function formatFoot(foot: DominantFoot | null): string {
  return foot ? ROTULO_PE[foot] : SEM_VALOR;
}

export function toAthleteProfileView(dto: AthleteProfileDTO): AthleteProfileView {
  const fullName = `${dto.first_name} ${dto.last_name}`;

  return {
    userId: dto.user_id,
    fullName,
    initial: fullName.charAt(0),
    positionLabel: formatPosition(dto.position),
    statusLabel: ROTULO_STATUS[dto.status],
    location: formatLocation(dto.city, dto.state),
    ageLabel: dto.age === null ? SEM_VALOR : String(dto.age),
    heightLabel: formatHeight(dto.height_cm),
    footLabel: formatFoot(dto.dominant_foot),
    currentClub: dto.current_club,
    bio: dto.bio,
    avatarUrl: dto.avatar_url,
    clipsCount: dto.clips_count,
  };
}
```

- [ ] **Step 5: Rodar e verificar que passam**

```bash
docker compose exec web npm test
```

Esperado: 12 passed nos mappers, além dos testes anteriores.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/
git commit -m "feat(frontend): extrai mappers puros do perfil do atleta"
```

---

### Task 15: `api.ts` e hook `useAthleteProfile`

**Files:**
- Create: `frontend/src/features/profiles/api.ts`
- Create: `frontend/src/shared/lib/queryClient.ts`
- Create: `frontend/src/features/profiles/hooks/useAthleteProfile.ts`
- Test: `frontend/src/features/profiles/hooks/useAthleteProfile.test.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Escrever os testes que falham**

`frontend/src/features/profiles/hooks/useAthleteProfile.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useAthleteProfile } from './useAthleteProfile';

const DTO = {
  user_id: 'abc',
  first_name: 'Jeh',
  last_name: 'Rodrigues',
  position: 'ATACANTE',
  status: 'DISPONIVEL',
  age: 19,
  height_cm: 178,
  dominant_foot: 'DESTRO',
  city: 'Campinas',
  state: 'SP',
  current_club: null,
  bio: null,
  avatar_url: null,
  clips_count: 42,
};

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe('useAthleteProfile', () => {
  it('comeca carregando', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    const { result } = renderHook(() => useAthleteProfile('abc'), { wrapper });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.profile).toBeUndefined();
  });

  it('devolve o view model ja formatado', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    const { result } = renderHook(() => useAthleteProfile('abc'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.profile?.fullName).toBe('Jeh Rodrigues');
    expect(result.current.profile?.heightLabel).toBe('1,78 m');
  });

  it('sinaliza notFound no 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Atleta nao encontrado.' }), { status: 404 })
    );

    const { result } = renderHook(() => useAthleteProfile('abc'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.notFound).toBe(true);
  });

  it('sinaliza erro generico em falha de servidor', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'boom' }), { status: 500 })
    );

    const { result } = renderHook(() => useAthleteProfile('abc'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(true);
    expect(result.current.notFound).toBe(false);
  });

  it('nao busca quando o id esta ausente', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    renderHook(() => useAthleteProfile(undefined), { wrapper });

    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Rodar e verificar que falham**

```bash
docker compose exec web npm test
```

Esperado: FAIL — `Failed to resolve import "./useAthleteProfile"`.

- [ ] **Step 3: Escrever o `api.ts` da feature**

`frontend/src/features/profiles/api.ts`:

```ts
import { httpGet, httpPut } from '../../shared/lib/httpClient';
import type { AthleteProfileDTO } from './types';

export function getAthleteProfile(userId: string): Promise<AthleteProfileDTO> {
  return httpGet<AthleteProfileDTO>(`/profiles/athletes/${userId}`);
}

export function getMyProfile(): Promise<AthleteProfileDTO> {
  return httpGet<AthleteProfileDTO>('/profiles/me');
}

export function updateMyProfile(
  changes: Partial<Omit<AthleteProfileDTO, 'user_id' | 'age' | 'clips_count'>>
): Promise<AthleteProfileDTO> {
  return httpPut<AthleteProfileDTO>('/profiles/me', changes);
}
```

- [ ] **Step 4: Escrever o `queryClient`**

`frontend/src/shared/lib/queryClient.ts`:

```ts
import { QueryClient } from '@tanstack/react-query';
import { ApiError } from './httpClient';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // Repetir um 404 ou um 401 e desperdicio: a resposta nao vai mudar.
      retry: (falhas, erro) => {
        if (erro instanceof ApiError && (erro.notFound || erro.unauthorized)) {
          return false;
        }
        return falhas < 2;
      },
    },
  },
});
```

- [ ] **Step 5: Escrever o hook**

`frontend/src/features/profiles/hooks/useAthleteProfile.ts`:

```ts
import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../../../shared/lib/httpClient';
import { getAthleteProfile } from '../api';
import { toAthleteProfileView } from '../mappers';
import type { AthleteProfileView } from '../types';

interface UseAthleteProfileResult {
  profile: AthleteProfileView | undefined;
  isLoading: boolean;
  isError: boolean;
  notFound: boolean;
}

export function useAthleteProfile(userId: string | undefined): UseAthleteProfileResult {
  const { data, isPending, isError, error, fetchStatus } = useQuery({
    queryKey: ['athlete-profile', userId],
    queryFn: () => getAthleteProfile(userId as string),
    enabled: Boolean(userId),
  });

  return {
    profile: data ? toAthleteProfileView(data) : undefined,
    // Com `enabled: false` o React Query fica pending mas ocioso; sem checar
    // fetchStatus a tela ficaria em "carregando" para sempre quando nao ha id.
    isLoading: isPending && fetchStatus !== 'idle',
    isError,
    notFound: error instanceof ApiError && error.notFound,
  };
}
```

- [ ] **Step 6: Adicionar o provider ao `main.tsx`**

Substituir o conteúdo de `frontend/src/main.tsx` por:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.js'
import { queryClient } from './shared/lib/queryClient'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
```

- [ ] **Step 7: Rodar e verificar que passam**

```bash
docker compose exec web npm test
```

Esperado: 5 passed no hook, suíte inteira verde.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/features/ frontend/src/shared/ frontend/src/main.tsx
git commit -m "feat(frontend): adiciona useAthleteProfile com tanstack query"
```

---

### Task 16: Componentes e página integrada

**Files:**
- Create: `frontend/src/features/profiles/components/ProfileHeader.tsx`
- Create: `frontend/src/features/profiles/components/QuickStats.tsx`
- Create: `frontend/src/features/profiles/components/AboutTab.tsx`
- Modify: `frontend/src/pages/PublicProfile/PublicProfile.tsx`
- Modify: `frontend/src/App.tsx:26`

- [ ] **Step 1: Criar `ProfileHeader`**

`frontend/src/features/profiles/components/ProfileHeader.tsx`:

```tsx
import { Activity, Bookmark, Check, MapPin, MessageCircle, Shield } from 'lucide-react';
import type { AthleteProfileView } from '../types';

interface Props {
  profile: AthleteProfileView;
}

/**
 * Cabecalho do perfil. Os botoes sociais ficam desabilitados nesta fatia:
 * Seguir/Salvar chegam na fatia 3 e Enviar Mensagem pertence ao M5.
 */
export function ProfileHeader({ profile }: Props) {
  return (
    <div className="profile-header-card">
      <div className="public-avatar">{profile.initial}</div>

      <div className="profile-main-info">
        <div className="profile-badges">
          <span className="badge badge-primary">
            <Shield size={14} /> {profile.positionLabel}
          </span>
          <span className="badge badge-success">
            <Activity size={14} /> {profile.statusLabel}
          </span>
        </div>

        <h1 className="profile-name">{profile.fullName}</h1>

        <div className="profile-location">
          <MapPin size={16} /> {profile.location}
        </div>
      </div>

      <div className="profile-actions">
        <button className="btn-secondary" disabled title="Disponivel em breve">
          <Check size={18} /> Seguir
        </button>
        <button className="btn-secondary" disabled title="Disponivel em breve">
          <Bookmark size={18} /> Salvar Atleta
        </button>
        <button className="btn-primary" disabled title="Disponivel em breve">
          <MessageCircle size={18} /> Enviar Mensagem
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Criar `QuickStats`**

`frontend/src/features/profiles/components/QuickStats.tsx`:

```tsx
import type { AthleteProfileView } from '../types';

interface Props {
  profile: AthleteProfileView;
}

export function QuickStats({ profile }: Props) {
  return (
    <div className="quick-stats-grid">
      <div className="stat-box">
        <div className="stat-label">Idade</div>
        <div className="stat-value">{profile.ageLabel}</div>
      </div>
      <div className="stat-box">
        <div className="stat-label">Pe Dominante</div>
        <div className="stat-value">{profile.footLabel}</div>
      </div>
      <div className="stat-box">
        <div className="stat-label">Altura</div>
        <div className="stat-value">{profile.heightLabel}</div>
      </div>
      <div className="stat-box">
        <div className="stat-label">Clipes Gerados IA</div>
        <div className="stat-value stat-value-highlight">{profile.clipsCount}</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Criar `AboutTab`**

`frontend/src/features/profiles/components/AboutTab.tsx`:

```tsx
import type { AthleteProfileView } from '../types';

interface Props {
  profile: AthleteProfileView;
}

/**
 * Aba Sobre: exibe a bio real. O "Historico" que existia aqui era texto fixo
 * inventado, sem lastro no dominio, e foi removido (secao 7.4 da spec).
 */
export function AboutTab({ profile }: Props) {
  return (
    <div className="about-tab">
      {profile.bio ? <p>{profile.bio}</p> : <p>Este atleta ainda nao escreveu uma bio.</p>}

      {profile.currentClub && (
        <p className="about-club">
          <strong>Clube atual:</strong> {profile.currentClub}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Acrescentar os estilos usados pelos componentes**

Ao final de `frontend/src/pages/PublicProfile/PublicProfile.css`:

```css
.profile-location {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
  color: rgba(255, 255, 255, 0.7);
}

.stat-value-highlight {
  color: #5badda;
}

.about-tab {
  padding: 2rem 0;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.8;
}

.about-club {
  margin-top: 1.5rem;
}

.tab-icon {
  display: inline;
  margin-right: 6px;
  margin-bottom: -4px;
}

.profile-state {
  padding: 4rem 0;
  text-align: center;
  color: rgba(255, 255, 255, 0.6);
}

.placeholder-tab {
  padding: 3rem 0;
  text-align: center;
  color: rgba(255, 255, 255, 0.5);
}

.placeholder-tab h3 {
  font-family: 'Outfit', sans-serif;
  color: #fff;
  font-size: 1.2rem;
}
```

- [ ] **Step 5: Reescrever a página**

Substituir o conteúdo de `frontend/src/pages/PublicProfile/PublicProfile.tsx` por:

```tsx
import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Activity, Info, Play } from 'lucide-react';
import { AboutTab } from '../../features/profiles/components/AboutTab';
import { ProfileHeader } from '../../features/profiles/components/ProfileHeader';
import { QuickStats } from '../../features/profiles/components/QuickStats';
import { useAthleteProfile } from '../../features/profiles/hooks/useAthleteProfile';
import './PublicProfile.css';

type Tab = 'clips' | 'analysis' | 'about';

export default function PublicProfile() {
  const { userId } = useParams<{ userId: string }>();
  const { profile, isLoading, isError, notFound } = useAthleteProfile(userId);
  const [activeTab, setActiveTab] = useState<Tab>('clips');

  if (isLoading) {
    return <div className="profile-state">Carregando perfil...</div>;
  }

  if (notFound) {
    return <div className="profile-state">Atleta nao encontrado.</div>;
  }

  if (isError || !profile) {
    return (
      <div className="profile-state">
        Nao foi possivel carregar o perfil. Tente novamente em instantes.
      </div>
    );
  }

  return (
    <div className="public-profile-root">
      <div className="profile-cover">
        <div className="profile-cover-pattern" />
      </div>

      <div className="public-profile-container">
        <ProfileHeader profile={profile} />
        <QuickStats profile={profile} />

        <div className="tabs-nav">
          <button
            className={`tab-btn ${activeTab === 'clips' ? 'active' : ''}`}
            onClick={() => setActiveTab('clips')}
          >
            <Play size={18} className="tab-icon" />
            Videoteca
          </button>
          <button
            className={`tab-btn ${activeTab === 'analysis' ? 'active' : ''}`}
            onClick={() => setActiveTab('analysis')}
          >
            <Activity size={18} className="tab-icon" />
            Analise Cinematica
          </button>
          <button
            className={`tab-btn ${activeTab === 'about' ? 'active' : ''}`}
            onClick={() => setActiveTab('about')}
          >
            <Info size={18} className="tab-icon" />
            Sobre
          </button>
        </div>

        <div className="tabs-content">
          {activeTab === 'clips' && (
            <div className="placeholder-tab">
              <Play size={48} />
              <h3>Videoteca em integracao</h3>
              <p>Os clipes reais chegam na proxima fatia.</p>
            </div>
          )}

          {activeTab === 'analysis' && (
            <div className="placeholder-tab">
              <Activity size={48} />
              <h3>Graficos em Desenvolvimento</h3>
              <p>Aqui entrarao os radares de desempenho.</p>
            </div>
          )}

          {activeTab === 'about' && <AboutTab profile={profile} />}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Mover a rota para dentro da área autenticada**

Em `frontend/src/App.tsx`, remover a linha:

```tsx
        <Route path="/public-profile" element={<PublicProfile />} />
```

E, dentro do bloco `<Route element={<MainLayout />}>`, abaixo de `/clips-history`,
acrescentar:

```tsx
            <Route path="/athletes/:userId" element={<PublicProfile />} />
```

- [ ] **Step 7: Verificar tipos e testes**

```bash
docker compose exec web npx tsc --noEmit
docker compose exec web npm test
```

Esperado: `tsc` sem saída (sucesso) e toda a suíte verde.

- [ ] **Step 8: Verificar no navegador**

```bash
docker compose exec api pytest -q
```

Esperado: toda a suíte do backend verde. Em seguida, com a aplicação no ar, fazer login,
copiar o `id` do usuário de `localStorage.user` e abrir `http://localhost:5173/athletes/<id>`.
Confirmar: nome real, badge de posição, estatísticas e a aba Sobre.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): integra a pagina de perfil do atleta com a api"
```

---

## Verificação final da fatia

- [ ] **Suíte completa do backend**

```bash
docker compose exec api pytest -v
```

- [ ] **Suíte completa do frontend**

```bash
docker compose exec web npm test
```

- [ ] **Migrações sobem e descem limpas**

```bash
docker compose exec api alembic -x db_url=postgresql://smartscout:smartscout@postgres-test:5432/smartscout_test downgrade base && \n  docker compose exec api alembic -x db_url=postgresql://smartscout:smartscout@postgres-test:5432/smartscout_test upgrade head
```

- [ ] **Migrações aplicam no banco de desenvolvimento**

Rodar `alembic upgrade head` apontando para o `DATABASE_URL` real, conferindo que o
backfill de `role` e dos perfis não falha em base com dados.

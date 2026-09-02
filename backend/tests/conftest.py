"""
Configuracao compartilhada por TODA a suite.

Este arquivo deve conter apenas o que e livre de banco. As fixtures que dependem de
Postgres vivem em `tests/integration/conftest.py`, para que `pytest tests/unit` rode
com o `postgres-test` desligado -- esse e o loop rapido de TDD.

A unica coisa feita aqui e apontar DATABASE_URL para o banco de teste, ANTES de
qualquer import de `app.*` em qualquer ponto da suite. E obrigatorio nessa ordem:
`app/core/database.py` le DATABASE_URL no momento do import e cria a engine ali. O
`load_dotenv()` que roda dentro daquele modulo nao sobrescreve variaveis ja definidas
(override=False e o padrao), entao o valor abaixo vence o backend/.env.

Definir a variavel nao abre conexao: `create_engine` so conecta no primeiro uso. Por
isso um teste unitario pode importar `app.*` sem exigir banco no ar.
"""
import os

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://smartscout:smartscout@postgres-test:5432/smartscout_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

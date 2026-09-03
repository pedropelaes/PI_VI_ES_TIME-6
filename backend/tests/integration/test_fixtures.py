"""
Guarda-trilho das fixtures de banco: prova que o `client` nao compartilha a Session do teste.

A fixture `client` nao sobrescreve `get_session`: os handlers usam a dependencia de
producao, que abre uma Session por request. Se alguem voltar a sobrescreve-la com a Session
do proprio teste (`lambda: session`), o handler e o corpo do teste passam a dividir um
identity map e uma transacao. As duas consequencias sao reais:

- um endpoint que esquece o `commit()` continua verde, porque o teste le o objeto sujo da
  sessao compartilhada;
- um caminho de erro que aborta a transacao (IntegrityError, DomainError sem rollback) deixa
  a Session inutilizavel, e as assercoes seguintes estouram PendingRollbackError escondendo
  a causa real.

Este arquivo existe para que uma volta acidental aquele atalho falhe aqui, e nao la na frente
como um falso verde em outro teste.
"""
from sqlalchemy import text
from sqlmodel import Session

from app.core.database import engine as app_engine
from app.core.security import hash_password
from app.modules.identity.models import User

from tests.integration.conftest import LOCK_TIMEOUT


def test_handler_nao_enxerga_escrita_nao_commitada_do_teste(client, session: Session):
    """Sem commit, o usuario nao existe para o request -- prova de transacoes separadas."""
    session.add(
        User(
            email="fantasma@teste.com",
            password_hash=hash_password("senha12345"),
            first_name="Fan",
            last_name="Tasma",
        )
    )
    session.flush()  # existe na Session do teste, mas nao no banco

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "fantasma@teste.com", "password": "senha12345"},
    )

    assert resp.status_code == 401, (
        "o handler enxergou uma escrita nao commitada: a fixture `client` voltou a "
        "compartilhar a Session do teste"
    )


def test_conexoes_tem_lock_timeout(engine, session: Session):
    """
    Contencao de lock tem que virar erro, nao pytest pendurado.

    Postgres espera por um lock indefinidamente por padrao. Como o handler agora roda numa
    Session propria, um teste que escreve sem commitar e depois faz um request que toca a
    mesma linha trava para sempre: o request espera o lock do teste, o teste espera o
    request. Com `lock_timeout` a espera termina num erro que nomeia a tabela.

    Cobre as duas pontas porque as duas saem da mesma engine: a Session do teste e a que o
    `get_session` de producao abre por request.
    """
    esperado = LOCK_TIMEOUT

    assert session.exec(text("SHOW lock_timeout")).scalar() == esperado

    with Session(app_engine) as por_request:
        assert por_request.exec(text("SHOW lock_timeout")).scalar() == esperado

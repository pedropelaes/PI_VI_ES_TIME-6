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
from sqlmodel import Session

from app.core.security import hash_password
from app.modules.identity.models import User


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


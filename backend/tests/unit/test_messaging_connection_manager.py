"""
Testes unitarios do ConnectionManager: nenhum precisa de rede real, so verificam quem
recebe o que dado um dicionario de sockets falsos.
"""
import uuid

import pytest

from app.modules.messaging.connection_manager import ConnectionManager

# So o plugin do anyio esta instalado (via httpx/starlette), nao o pytest-asyncio: os
# testes daqui usam o marcador `anyio` em vez de `asyncio`, com o backend fixado em
# asyncio (o unico que o projeto roda) via a fixture abaixo.
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeWebSocket:
    def __init__(self, falha_no_envio: bool = False):
        self.accepted = False
        self.sent: list[dict] = []
        self._falha_no_envio = falha_no_envio

    async def accept(self):
        self.accepted = True

    async def send_json(self, payload: dict):
        if self._falha_no_envio:
            raise RuntimeError("conexao fechada")
        self.sent.append(payload)


async def test_connect_aceita_o_socket_e_registra_o_usuario():
    manager = ConnectionManager()
    user_id = uuid.uuid4()
    ws = FakeWebSocket()

    await manager.connect(user_id, ws)

    assert ws.accepted is True


async def test_send_to_user_entrega_para_todas_as_conexoes_do_mesmo_usuario():
    """A mesma pessoa pode ter a Inbox aberta em duas abas."""
    manager = ConnectionManager()
    user_id = uuid.uuid4()
    aba1, aba2 = FakeWebSocket(), FakeWebSocket()

    await manager.connect(user_id, aba1)
    await manager.connect(user_id, aba2)
    await manager.send_to_user(user_id, {"type": "new_message"})

    assert aba1.sent == [{"type": "new_message"}]
    assert aba2.sent == [{"type": "new_message"}]


async def test_send_to_user_nao_afeta_outros_usuarios():
    manager = ConnectionManager()
    destinatario, outro = uuid.uuid4(), uuid.uuid4()
    ws_destinatario, ws_outro = FakeWebSocket(), FakeWebSocket()

    await manager.connect(destinatario, ws_destinatario)
    await manager.connect(outro, ws_outro)
    await manager.send_to_user(destinatario, {"type": "new_message"})

    assert ws_destinatario.sent == [{"type": "new_message"}]
    assert ws_outro.sent == []


async def test_send_to_user_sem_conexao_nao_estoura():
    manager = ConnectionManager()
    await manager.send_to_user(uuid.uuid4(), {"type": "new_message"})


async def test_disconnect_remove_o_socket_e_nao_recebe_mais_eventos():
    manager = ConnectionManager()
    user_id = uuid.uuid4()
    ws = FakeWebSocket()

    await manager.connect(user_id, ws)
    manager.disconnect(user_id, ws)
    await manager.send_to_user(user_id, {"type": "new_message"})

    assert ws.sent == []


async def test_socket_morto_e_removido_ao_falhar_o_envio():
    """
    Uma aba fechada abruptamente (rede caiu) nao dispara disconnect(): o socket so
    e descoberto morto quando send_to_user tenta usa-lo, e deve se auto-limpar.
    """
    manager = ConnectionManager()
    user_id = uuid.uuid4()
    vivo = FakeWebSocket()
    morto = FakeWebSocket(falha_no_envio=True)

    await manager.connect(user_id, vivo)
    await manager.connect(user_id, morto)
    await manager.send_to_user(user_id, {"type": "new_message"})

    assert vivo.sent == [{"type": "new_message"}]

    # Uma segunda entrega nao tenta mais o socket morto (senao o teste acima ja teria
    # levantado a excecao de novo antes de chegar aqui).
    await manager.send_to_user(user_id, {"type": "new_message"})
    assert vivo.sent == [{"type": "new_message"}, {"type": "new_message"}]

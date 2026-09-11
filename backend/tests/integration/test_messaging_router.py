"""Testes de integracao do chat interno: TestClient contra o banco de teste."""
import uuid

import pytest

from app.core.security import create_access_token, hash_password
from app.modules.identity.models import User, UserRole
from app.modules.profiles.models import AthleteProfile, ScoutProfile


def _cria_usuario(session, email: str, role: UserRole, first: str, last: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("senha12345"),
        first_name=first,
        last_name=last,
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def _token(user: User) -> str:
    return create_access_token(str(user.id))


@pytest.fixture
def scout(session) -> User:
    user = _cria_usuario(session, "scout.chat@teste.com", UserRole.SCOUT, "Ana", "Souza")
    session.add(ScoutProfile(user_id=user.id, avatar_path="avatars/ana.png"))
    session.commit()
    return user


@pytest.fixture
def headers_scout(scout) -> dict[str, str]:
    return _headers(scout)


@pytest.fixture
def terceiro(session) -> User:
    return _cria_usuario(session, "terceiro.chat@teste.com", UserRole.CLUB, "Clube", "C")


@pytest.fixture
def headers_terceiro(terceiro) -> dict[str, str]:
    return _headers(terceiro)


@pytest.fixture
def perfil_atleta(session, usuario) -> AthleteProfile:
    p = AthleteProfile(user_id=usuario.id, avatar_path="avatars/jeh.png")
    session.add(p)
    session.commit()
    return p


# ---------------------------------------------------------------------------
# Autenticacao
# ---------------------------------------------------------------------------

def test_sem_jwt_devolve_401(client):
    resposta = client.get("/api/v1/messages/conversations")
    assert resposta.status_code == 401


# ---------------------------------------------------------------------------
# Listagem
# ---------------------------------------------------------------------------

def test_lista_vazia_quando_nao_ha_conversas(client, auth_headers):
    resposta = client.get("/api/v1/messages/conversations", headers=auth_headers)
    assert resposta.status_code == 200
    assert resposta.json() == []


# ---------------------------------------------------------------------------
# Criacao / reaproveitamento de conversa
# ---------------------------------------------------------------------------

def test_avatar_do_participante_vem_do_perfil_do_papel_dele(
    client, headers_scout, usuario, scout, perfil_atleta
):
    """O avatar mora na tabela de perfil (athlete/scout/club), nao em `users`."""
    resposta = client.post(
        "/api/v1/messages/conversations", headers=headers_scout, json={"recipient_id": str(usuario.id)}
    )
    assert resposta.json()["participant"]["avatar_url"] == "avatars/jeh.png"


def test_cria_conversa_com_outro_usuario(client, auth_headers, scout):
    resposta = client.post(
        "/api/v1/messages/conversations",
        headers=auth_headers,
        json={"recipient_id": str(scout.id)},
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["participant"]["id"] == str(scout.id)
    assert corpo["participant"]["role"] == "SCOUT"
    assert corpo["participant"]["avatar_url"] == "avatars/ana.png"
    assert corpo["last_message"] is None
    assert corpo["unread_count"] == 0


def test_criar_conversa_duas_vezes_reaproveita_a_mesma(client, auth_headers, scout):
    primeira = client.post(
        "/api/v1/messages/conversations", headers=auth_headers, json={"recipient_id": str(scout.id)}
    ).json()
    segunda = client.post(
        "/api/v1/messages/conversations", headers=auth_headers, json={"recipient_id": str(scout.id)}
    ).json()

    assert primeira["id"] == segunda["id"]


def test_criar_conversa_e_simetrica_entre_os_dois_participantes(client, auth_headers, headers_scout, usuario, scout):
    """A conversa que o atleta abre com o scout e a mesma que o scout ve com o atleta."""
    do_atleta = client.post(
        "/api/v1/messages/conversations", headers=auth_headers, json={"recipient_id": str(scout.id)}
    ).json()
    do_scout = client.post(
        "/api/v1/messages/conversations", headers=headers_scout, json={"recipient_id": str(usuario.id)}
    ).json()

    assert do_atleta["id"] == do_scout["id"]


def test_criar_conversa_com_destinatario_inexistente_devolve_404(client, auth_headers):
    resposta = client.post(
        "/api/v1/messages/conversations",
        headers=auth_headers,
        json={"recipient_id": str(uuid.uuid4())},
    )
    assert resposta.status_code == 404


def test_criar_conversa_consigo_mesmo_devolve_422(client, auth_headers, usuario):
    resposta = client.post(
        "/api/v1/messages/conversations",
        headers=auth_headers,
        json={"recipient_id": str(usuario.id)},
    )
    assert resposta.status_code == 422


# ---------------------------------------------------------------------------
# Mensagens
# ---------------------------------------------------------------------------

def _conversa_id(client, headers, recipient_id) -> str:
    return client.post(
        "/api/v1/messages/conversations", headers=headers, json={"recipient_id": str(recipient_id)}
    ).json()["id"]


def test_envia_e_le_mensagem(client, auth_headers, scout):
    conversation_id = _conversa_id(client, auth_headers, scout.id)

    envio = client.post(
        f"/api/v1/messages/conversations/{conversation_id}/messages",
        headers=auth_headers,
        json={"body": "Olá, tudo bem?"},
    )
    assert envio.status_code == 201
    assert envio.json()["body"] == "Olá, tudo bem?"
    assert envio.json()["read_at"] is None

    leitura = client.get(
        f"/api/v1/messages/conversations/{conversation_id}/messages", headers=auth_headers
    )
    assert leitura.status_code == 200
    corpo = leitura.json()
    assert corpo["has_more"] is False
    assert [m["body"] for m in corpo["messages"]] == ["Olá, tudo bem?"]


def test_mensagens_ficam_em_ordem_cronologica(client, auth_headers, scout):
    conversation_id = _conversa_id(client, auth_headers, scout.id)

    for texto in ["primeira", "segunda", "terceira"]:
        client.post(
            f"/api/v1/messages/conversations/{conversation_id}/messages",
            headers=auth_headers,
            json={"body": texto},
        )

    corpo = client.get(
        f"/api/v1/messages/conversations/{conversation_id}/messages", headers=auth_headers
    ).json()

    assert [m["body"] for m in corpo["messages"]] == ["primeira", "segunda", "terceira"]


def test_list_messages_paginacao_sinaliza_has_more(client, auth_headers, scout):
    conversation_id = _conversa_id(client, auth_headers, scout.id)

    for i in range(3):
        client.post(
            f"/api/v1/messages/conversations/{conversation_id}/messages",
            headers=auth_headers,
            json={"body": f"msg {i}"},
        )

    corpo = client.get(
        f"/api/v1/messages/conversations/{conversation_id}/messages?limit=2",
        headers=auth_headers,
    ).json()

    assert corpo["has_more"] is True
    assert [m["body"] for m in corpo["messages"]] == ["msg 1", "msg 2"]


def test_mensagem_so_com_espacos_devolve_422(client, auth_headers, scout):
    conversation_id = _conversa_id(client, auth_headers, scout.id)

    resposta = client.post(
        f"/api/v1/messages/conversations/{conversation_id}/messages",
        headers=auth_headers,
        json={"body": "   "},
    )
    assert resposta.status_code == 422


def test_enviar_mensagem_em_conversa_alheia_devolve_403(
    client, auth_headers, headers_terceiro, scout
):
    conversation_id = _conversa_id(client, auth_headers, scout.id)

    resposta = client.post(
        f"/api/v1/messages/conversations/{conversation_id}/messages",
        headers=headers_terceiro,
        json={"body": "intrometido"},
    )
    assert resposta.status_code == 403


def test_ler_mensagens_de_conversa_alheia_devolve_403(client, auth_headers, headers_terceiro, scout):
    conversation_id = _conversa_id(client, auth_headers, scout.id)

    resposta = client.get(
        f"/api/v1/messages/conversations/{conversation_id}/messages", headers=headers_terceiro
    )
    assert resposta.status_code == 403


def test_conversa_inexistente_devolve_404(client, auth_headers):
    resposta = client.get(
        f"/api/v1/messages/conversations/{uuid.uuid4()}/messages", headers=auth_headers
    )
    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# Nao lidas e marcacao de leitura
# ---------------------------------------------------------------------------

def test_lista_de_conversas_mostra_ultima_mensagem_e_nao_lidas(
    client, auth_headers, headers_scout, scout
):
    conversation_id = _conversa_id(client, auth_headers, scout.id)
    client.post(
        f"/api/v1/messages/conversations/{conversation_id}/messages",
        headers=auth_headers,
        json={"body": "oi scout"},
    )
    client.post(
        f"/api/v1/messages/conversations/{conversation_id}/messages",
        headers=headers_scout,
        json={"body": "oi atleta"},
    )

    lista_do_atleta = client.get("/api/v1/messages/conversations", headers=auth_headers).json()
    assert len(lista_do_atleta) == 1
    assert lista_do_atleta[0]["last_message"]["body"] == "oi atleta"
    assert lista_do_atleta[0]["unread_count"] == 1


def test_marcar_como_lida_zera_nao_lidas(client, auth_headers, headers_scout, scout):
    conversation_id = _conversa_id(client, auth_headers, scout.id)
    client.post(
        f"/api/v1/messages/conversations/{conversation_id}/messages",
        headers=headers_scout,
        json={"body": "oi atleta"},
    )

    marcado = client.post(
        f"/api/v1/messages/conversations/{conversation_id}/read", headers=auth_headers
    )
    assert marcado.status_code == 204

    lista = client.get("/api/v1/messages/conversations", headers=auth_headers).json()
    assert lista[0]["unread_count"] == 0


def test_marcar_como_lida_nao_afeta_as_proprias_mensagens_do_leitor(
    client, auth_headers, headers_scout, scout
):
    """Ler a conversa nao marca como lidas mensagens que o proprio autenticado enviou."""
    conversation_id = _conversa_id(client, auth_headers, scout.id)
    client.post(
        f"/api/v1/messages/conversations/{conversation_id}/messages",
        headers=auth_headers,
        json={"body": "oi scout"},
    )

    client.post(f"/api/v1/messages/conversations/{conversation_id}/read", headers=auth_headers)

    mensagens = client.get(
        f"/api/v1/messages/conversations/{conversation_id}/messages", headers=auth_headers
    ).json()["messages"]
    assert mensagens[0]["read_at"] is None


def test_unread_count_soma_todas_as_conversas(client, auth_headers, headers_scout, scout, terceiro, headers_terceiro):
    conversa_scout = _conversa_id(client, auth_headers, scout.id)
    conversa_terceiro = _conversa_id(client, auth_headers, terceiro.id)

    client.post(
        f"/api/v1/messages/conversations/{conversa_scout}/messages",
        headers=headers_scout,
        json={"body": "1"},
    )
    client.post(
        f"/api/v1/messages/conversations/{conversa_terceiro}/messages",
        headers=headers_terceiro,
        json={"body": "2"},
    )

    total = client.get("/api/v1/messages/unread-count", headers=auth_headers).json()
    assert total["count"] == 2


# ---------------------------------------------------------------------------
# WebSocket: entrega em tempo real
# ---------------------------------------------------------------------------

def test_websocket_sem_token_e_recusado(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/messages/ws"):
            pass


def test_websocket_com_token_invalido_e_recusado(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/messages/ws?token=lixo"):
            pass


def test_websocket_recebe_nova_mensagem_em_tempo_real(client, auth_headers, usuario, scout):
    """
    O scout fica conectado no WS; o atleta manda uma mensagem por HTTP normal (o POST
    continua sendo quem persiste); o scout deve receber o evento no socket, sem precisar
    dar um novo GET.
    """
    conversation_id = _conversa_id(client, auth_headers, scout.id)

    with client.websocket_connect(f"/api/v1/messages/ws?token={_token(scout)}") as ws:
        client.post(
            f"/api/v1/messages/conversations/{conversation_id}/messages",
            headers=auth_headers,
            json={"body": "chegou?"},
        )

        evento = ws.receive_json()

    assert evento["type"] == "new_message"
    assert evento["message"]["body"] == "chegou?"
    assert evento["message"]["sender_id"] == str(usuario.id)
    assert evento["message"]["conversation_id"] == conversation_id


def test_websocket_recebe_evento_para_o_proprio_remetente(client, auth_headers, usuario, scout):
    """Outra aba do proprio remetente tambem deve saber que a mensagem saiu."""
    conversation_id = _conversa_id(client, auth_headers, scout.id)

    with client.websocket_connect(f"/api/v1/messages/ws?token={_token(usuario)}") as ws:
        client.post(
            f"/api/v1/messages/conversations/{conversation_id}/messages",
            headers=auth_headers,
            json={"body": "para mim mesmo em outra aba"},
        )

        evento = ws.receive_json()

    assert evento["type"] == "new_message"
    assert evento["message"]["body"] == "para mim mesmo em outra aba"


def test_websocket_recebe_evento_de_leitura(client, auth_headers, headers_scout, usuario, scout):
    """
    Quando o scout marca a conversa como lida, o atleta (que mandou a mensagem) deve
    receber um evento -- e o que liga os dois riscos azuis na hora.
    """
    conversation_id = _conversa_id(client, auth_headers, scout.id)
    client.post(
        f"/api/v1/messages/conversations/{conversation_id}/messages",
        headers=auth_headers,
        json={"body": "oi scout"},
    )

    with client.websocket_connect(f"/api/v1/messages/ws?token={_token(usuario)}") as ws:
        client.post(
            f"/api/v1/messages/conversations/{conversation_id}/read", headers=headers_scout
        )

        evento = ws.receive_json()

    assert evento == {"type": "conversation_read", "conversation_id": conversation_id}


def test_websocket_nao_recebe_evento_de_outra_conversa(
    client, auth_headers, headers_scout, headers_terceiro, usuario, scout, terceiro
):
    """O socket do atleta so recebe eventos das conversas em que ele participa."""
    conversation_id = _conversa_id(client, auth_headers, scout.id)
    conversa_alheia_id = _conversa_id(client, headers_terceiro, scout.id)

    with client.websocket_connect(f"/api/v1/messages/ws?token={_token(usuario)}") as ws:
        # Mensagem numa conversa da qual o atleta NAO participa: se o manager
        # confundisse o destinatario, seria isto que o proximo receive_json pegaria.
        client.post(
            f"/api/v1/messages/conversations/{conversa_alheia_id}/messages",
            headers=headers_terceiro,
            json={"body": "conversa alheia, o atleta nao deveria ver isto"},
        )
        client.post(
            f"/api/v1/messages/conversations/{conversation_id}/messages",
            headers=auth_headers,
            json={"body": "so eu devo receber isso"},
        )
        evento = ws.receive_json()
        assert evento["message"]["body"] == "so eu devo receber isso"

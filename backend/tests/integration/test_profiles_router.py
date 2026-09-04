"""Testes de integracao das rotas de perfil: TestClient contra o banco de teste."""
import uuid
from datetime import date

import pytest

from app.core.security import create_access_token, hash_password
from app.modules.identity.models import User, UserRole
from app.modules.profiles.models import (
    AthleteProfile,
    AthleteStatus,
    ClubProfile,
    DominantFoot,
    Position,
    ScoutProfile,
)


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
        avatar_path="avatars/jeh.png",
        status=AthleteStatus.DISPONIVEL,
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


@pytest.fixture
def usuario_scout(session) -> User:
    return _cria_usuario(session, "scout@teste.com", UserRole.SCOUT, "Ana", "Souza")


@pytest.fixture
def headers_scout(usuario_scout) -> dict[str, str]:
    return _headers(usuario_scout)


@pytest.fixture
def perfil_scout(session, usuario_scout) -> ScoutProfile:
    p = ScoutProfile(
        user_id=usuario_scout.id,
        organization="Cruzeiro",
        credential="CBF-1234",
        state="MG",
        city="Belo Horizonte",
        bio="Olheiro de base.",
        avatar_path="avatars/ana.png",
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


@pytest.fixture
def usuario_clube(session) -> User:
    return _cria_usuario(session, "clube@teste.com", UserRole.CLUB, "Clube", "Atletico")


@pytest.fixture
def headers_clube(usuario_clube) -> dict[str, str]:
    return _headers(usuario_clube)


@pytest.fixture
def perfil_clube(session, usuario_clube) -> ClubProfile:
    p = ClubProfile(
        user_id=usuario_clube.id,
        legal_name="Clube Atletico LTDA",
        cnpj="12345678000199",
        categories=["SUB_15", "SUB_17"],
        state="SP",
        city="Santos",
        bio="Clube formador.",
        avatar_path="avatars/clube.png",
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


# ---------------------------------------------------------------------------
# Leitura publica -- atleta
# ---------------------------------------------------------------------------

def test_sem_jwt_devolve_401(client, usuario):
    # Nesta versao do FastAPI (0.133.1), HTTPBearer.make_not_authenticated_error usa
    # HTTP_401_UNAUTHORIZED quando o header Authorization esta ausente -- versoes mais
    # antigas devolviam 403 nesse caso, mas nao e o que esta instalado aqui (confirmado
    # lendo fastapi.security.HTTPBearer.__call__ dentro do container).
    resposta = client.get(f"/api/v1/profiles/athletes/{usuario.id}")
    assert resposta.status_code == 401


@pytest.mark.parametrize("rota", ["scouts", "clubs"])
def test_rotas_novas_sem_jwt_devolvem_401(client, usuario, rota):
    assert client.get(f"/api/v1/profiles/{rota}/{usuario.id}").status_code == 401


def test_devolve_o_perfil_do_atleta(client, auth_headers, usuario, perfil):
    resposta = client.get(f"/api/v1/profiles/athletes/{usuario.id}", headers=auth_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["user_id"] == str(usuario.id)
    assert corpo["first_name"] == "Jeh"
    assert corpo["last_name"] == "Rodrigues"
    assert corpo["position"] == "ATACANTE"
    assert corpo["height_cm"] == 178
    assert corpo["dominant_foot"] == "DESTRO"
    assert corpo["city"] == "Campinas"
    assert corpo["state"] == "SP"
    assert corpo["current_club"] is None
    assert corpo["bio"] == "Atleta de base."
    assert corpo["avatar_url"] == "avatars/jeh.png"
    assert corpo["status"] == "DISPONIVEL"
    assert corpo["clips_count"] == 0
    assert isinstance(corpo["age"], int)


def test_campos_sociais_nao_estao_no_contrato_da_fatia_1(client, auth_headers, usuario, perfil):
    corpo = client.get(f"/api/v1/profiles/athletes/{usuario.id}", headers=auth_headers).json()
    assert "is_followed_by_me" not in corpo
    assert "is_saved_by_me" not in corpo


def test_id_inexistente_devolve_404(client, auth_headers):
    resposta = client.get(f"/api/v1/profiles/athletes/{uuid.uuid4()}", headers=auth_headers)
    assert resposta.status_code == 404


def test_usuario_sem_perfil_de_atleta_devolve_404(client, auth_headers, usuario):
    resposta = client.get(f"/api/v1/profiles/athletes/{usuario.id}", headers=auth_headers)
    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# Leitura publica -- scout e clube
# ---------------------------------------------------------------------------

def test_devolve_o_perfil_do_scout(client, auth_headers, usuario_scout, perfil_scout):
    resposta = client.get(
        f"/api/v1/profiles/scouts/{usuario_scout.id}", headers=auth_headers
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["user_id"] == str(usuario_scout.id)
    assert corpo["first_name"] == "Ana"
    assert corpo["last_name"] == "Souza"
    assert corpo["organization"] == "Cruzeiro"
    assert corpo["credential"] == "CBF-1234"
    assert corpo["city"] == "Belo Horizonte"
    assert corpo["state"] == "MG"
    assert corpo["bio"] == "Olheiro de base."
    assert corpo["avatar_url"] == "avatars/ana.png"


def test_perfil_de_scout_nao_tem_conceitos_de_atleta(
    client, auth_headers, usuario_scout, perfil_scout
):
    """`age` e `clips_count` sao de atleta (secao 4.1) e nao podem vazar para os outros."""
    corpo = client.get(
        f"/api/v1/profiles/scouts/{usuario_scout.id}", headers=auth_headers
    ).json()
    assert "age" not in corpo
    assert "clips_count" not in corpo


def test_devolve_o_perfil_do_clube(client, auth_headers, usuario_clube, perfil_clube):
    resposta = client.get(
        f"/api/v1/profiles/clubs/{usuario_clube.id}", headers=auth_headers
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["user_id"] == str(usuario_clube.id)
    assert corpo["first_name"] == "Clube"
    assert corpo["legal_name"] == "Clube Atletico LTDA"
    assert corpo["cnpj"] == "12345678000199"
    assert corpo["categories"] == ["SUB_15", "SUB_17"]
    assert corpo["city"] == "Santos"
    assert corpo["state"] == "SP"
    assert corpo["avatar_url"] == "avatars/clube.png"


def test_perfil_de_clube_nao_tem_conceitos_de_atleta(
    client, auth_headers, usuario_clube, perfil_clube
):
    corpo = client.get(
        f"/api/v1/profiles/clubs/{usuario_clube.id}", headers=auth_headers
    ).json()
    assert "age" not in corpo
    assert "clips_count" not in corpo


@pytest.mark.parametrize("rota", ["scouts", "clubs"])
def test_id_inexistente_nas_rotas_novas_devolve_404(client, auth_headers, rota):
    resposta = client.get(f"/api/v1/profiles/{rota}/{uuid.uuid4()}", headers=auth_headers)
    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# Cruzamento de papeis: cada rota so enxerga o seu (secao 4.1 da spec)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rota_alheia", ["scouts", "clubs"])
def test_id_de_atleta_nas_outras_rotas_devolve_404(
    client, auth_headers, usuario, perfil, rota_alheia
):
    resposta = client.get(
        f"/api/v1/profiles/{rota_alheia}/{usuario.id}", headers=auth_headers
    )
    assert resposta.status_code == 404


@pytest.mark.parametrize("rota_alheia", ["athletes", "clubs"])
def test_id_de_scout_nas_outras_rotas_devolve_404(
    client, auth_headers, usuario_scout, perfil_scout, rota_alheia
):
    resposta = client.get(
        f"/api/v1/profiles/{rota_alheia}/{usuario_scout.id}", headers=auth_headers
    )
    assert resposta.status_code == 404


@pytest.mark.parametrize("rota_alheia", ["athletes", "scouts"])
def test_id_de_clube_nas_outras_rotas_devolve_404(
    client, auth_headers, usuario_clube, perfil_clube, rota_alheia
):
    resposta = client.get(
        f"/api/v1/profiles/{rota_alheia}/{usuario_clube.id}", headers=auth_headers
    )
    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# /me polimorfico (decisoes Q3 e Q4)
# ---------------------------------------------------------------------------

def test_me_devolve_role_e_perfil_do_atleta(client, auth_headers, usuario, perfil):
    resposta = client.get("/api/v1/profiles/me", headers=auth_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["role"] == "ATHLETE"
    assert corpo["profile"]["city"] == "Campinas"
    assert corpo["profile"]["position"] == "ATACANTE"
    assert corpo["profile"]["clips_count"] == 0


def test_me_devolve_role_e_perfil_do_scout(client, headers_scout, perfil_scout):
    resposta = client.get("/api/v1/profiles/me", headers=headers_scout)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["role"] == "SCOUT"
    assert corpo["profile"]["organization"] == "Cruzeiro"
    assert corpo["profile"]["credential"] == "CBF-1234"
    assert "clips_count" not in corpo["profile"]


def test_me_devolve_role_e_perfil_do_clube(client, headers_clube, perfil_clube):
    resposta = client.get("/api/v1/profiles/me", headers=headers_clube)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["role"] == "CLUB"
    assert corpo["profile"]["legal_name"] == "Clube Atletico LTDA"
    assert corpo["profile"]["categories"] == ["SUB_15", "SUB_17"]
    assert "age" not in corpo["profile"]


def test_put_me_atualiza_apenas_os_campos_enviados(client, auth_headers, perfil):
    resposta = client.put(
        "/api/v1/profiles/me", headers=auth_headers, json={"city": "Santos"}
    )
    assert resposta.status_code == 200
    corpo = resposta.json()["profile"]
    assert corpo["city"] == "Santos"
    assert corpo["state"] == "SP"
    assert corpo["height_cm"] == 178


def test_put_me_reflete_no_get_seguinte(client, auth_headers, usuario, perfil):
    client.put("/api/v1/profiles/me", headers=auth_headers, json={"status": "CONTRATADO"})
    corpo = client.get(
        f"/api/v1/profiles/athletes/{usuario.id}", headers=auth_headers
    ).json()
    assert corpo["status"] == "CONTRATADO"


def test_put_me_de_scout_reflete_no_get_seguinte(
    client, headers_scout, usuario_scout, perfil_scout
):
    """Prova o commit do handler: a leitura seguinte usa outra Session (ver conftest)."""
    resposta = client.put(
        "/api/v1/profiles/me", headers=headers_scout, json={"organization": "Atletico"}
    )
    assert resposta.status_code == 200
    assert resposta.json()["role"] == "SCOUT"

    corpo = client.get(
        f"/api/v1/profiles/scouts/{usuario_scout.id}", headers=headers_scout
    ).json()
    assert corpo["organization"] == "Atletico"
    assert corpo["credential"] == "CBF-1234"


def test_put_me_de_clube_troca_as_categorias(
    client, headers_clube, usuario_clube, perfil_clube
):
    resposta = client.put(
        "/api/v1/profiles/me",
        headers=headers_clube,
        json={"categories": ["SUB_20", "PROFISSIONAL"]},
    )
    assert resposta.status_code == 200

    corpo = client.get(
        f"/api/v1/profiles/clubs/{usuario_clube.id}", headers=headers_clube
    ).json()
    assert corpo["categories"] == ["SUB_20", "PROFISSIONAL"]
    assert corpo["legal_name"] == "Clube Atletico LTDA"


def test_put_me_com_altura_invalida_devolve_422(client, auth_headers, perfil):
    resposta = client.put(
        "/api/v1/profiles/me", headers=auth_headers, json={"height_cm": 12}
    )
    assert resposta.status_code == 422


def test_put_me_de_clube_com_categoria_invalida_devolve_422(
    client, headers_clube, perfil_clube
):
    resposta = client.put(
        "/api/v1/profiles/me", headers=headers_clube, json={"categories": ["SUB_9"]}
    )
    assert resposta.status_code == 422


def test_put_me_de_scout_com_campo_de_atleta_devolve_422(
    client, headers_scout, perfil_scout
):
    """Secao 4.2: enviar um campo que nao pertence ao papel do autenticado e 422."""
    resposta = client.put(
        "/api/v1/profiles/me", headers=headers_scout, json={"position": "ATACANTE"}
    )
    assert resposta.status_code == 422


def test_put_me_de_atleta_com_campo_de_scout_devolve_422(client, auth_headers, perfil):
    resposta = client.put(
        "/api/v1/profiles/me", headers=auth_headers, json={"organization": "Cruzeiro"}
    )
    assert resposta.status_code == 422


def test_put_me_de_clube_com_campo_de_scout_devolve_422(
    client, headers_clube, perfil_clube
):
    resposta = client.put(
        "/api/v1/profiles/me", headers=headers_clube, json={"credential": "CBF-1"}
    )
    assert resposta.status_code == 422


def test_put_me_de_scout_com_campo_de_atleta_nao_grava_o_campo_valido(
    client, headers_scout, usuario_scout, perfil_scout
):
    """O 422 rejeita o payload inteiro -- nao aplica a parte valida e descarta o resto."""
    client.put(
        "/api/v1/profiles/me",
        headers=headers_scout,
        json={"city": "Contagem", "position": "ATACANTE"},
    )

    corpo = client.get(
        f"/api/v1/profiles/scouts/{usuario_scout.id}", headers=headers_scout
    ).json()
    assert corpo["city"] == "Belo Horizonte"


def test_put_me_sem_perfil_de_atleta_devolve_404(client, auth_headers, usuario):
    """
    Usuario autenticado mas sem linha em AthleteProfile -- caso real de quem foi
    cadastrado antes de `register` passar a criar o perfil junto (ou de qualquer
    inconsistencia equivalente). O repositorio devolve None e o service traduz para
    NotFoundError; aqui so travamos o contrato HTTP desse caminho, que antes so
    acontecia por construcao (fixture `perfil` sempre presente nos outros testes).
    """
    resposta = client.put(
        "/api/v1/profiles/me", headers=auth_headers, json={"city": "Santos"}
    )
    assert resposta.status_code == 404


def test_get_me_sem_perfil_do_papel_devolve_404(client, headers_scout):
    """Mesma inconsistencia do caso acima, agora pelo caminho polimorfico de leitura."""
    assert client.get("/api/v1/profiles/me", headers=headers_scout).status_code == 404

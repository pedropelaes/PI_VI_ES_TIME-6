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
    # Nesta versao do FastAPI (0.133.1), HTTPBearer.make_not_authenticated_error usa
    # HTTP_401_UNAUTHORIZED quando o header Authorization esta ausente -- versoes mais
    # antigas devolviam 403 nesse caso, mas nao e o que esta instalado aqui (confirmado
    # lendo fastapi.security.HTTPBearer.__call__ dentro do container).
    resposta = client.get(f"/api/v1/profiles/athletes/{usuario.id}")
    assert resposta.status_code == 401


def test_devolve_o_perfil_do_atleta(client, auth_headers, usuario, perfil):
    resposta = client.get(f"/api/v1/profiles/athletes/{usuario.id}", headers=auth_headers)

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
    corpo = client.get(f"/api/v1/profiles/athletes/{usuario.id}", headers=auth_headers).json()
    assert "is_followed_by_me" not in corpo
    assert "is_saved_by_me" not in corpo


def test_id_inexistente_devolve_404(client, auth_headers):
    resposta = client.get(f"/api/v1/profiles/athletes/{uuid.uuid4()}", headers=auth_headers)
    assert resposta.status_code == 404


def test_usuario_sem_perfil_de_atleta_devolve_404(client, auth_headers, usuario):
    resposta = client.get(f"/api/v1/profiles/athletes/{usuario.id}", headers=auth_headers)
    assert resposta.status_code == 404


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
    client.put("/api/v1/profiles/me", headers=auth_headers, json={"status": "CONTRATADO"})
    corpo = client.get(
        f"/api/v1/profiles/athletes/{usuario.id}", headers=auth_headers
    ).json()
    assert corpo["status"] == "CONTRATADO"


def test_put_me_com_altura_invalida_devolve_422(client, auth_headers, perfil):
    resposta = client.put(
        "/api/v1/profiles/me", headers=auth_headers, json={"height_cm": 12}
    )
    assert resposta.status_code == 422

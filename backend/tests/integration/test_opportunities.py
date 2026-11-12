"""
Peneiras e inscrições: /api/v1/opportunities.
Spec: docs/superpowers/specs/2026-11-11-oportunidades-peneiras-design.md
"""
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.main import app
from app.modules.opportunities.router import get_now
from app.core.security import create_access_token, hash_password
from app.modules.identity.models import User, UserRole
from app.modules.opportunities.models import (
    Opportunity,
    OpportunityApplication,
    OpportunityMode,
)
from app.modules.profiles.models import AthleteProfile, Position

AGORA = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)

@pytest.fixture(autouse=True)
def _agora_fixo():
    app.dependency_overrides[get_now] = lambda: (lambda: AGORA)
    yield
    app.dependency_overrides.pop(get_now, None)


def _payload(**over) -> dict:
    base = dict(
        title="Peneira Sub-17",
        description="Avaliação técnica e física.",
        mode="PRESENCIAL",
        state="SP",
        city="Campinas",
        address="Rua A, 100",
        event_at=(AGORA + timedelta(days=10)).isoformat(),
        registration_deadline=(AGORA + timedelta(days=5)).isoformat(),
    )
    base.update(over)
    return base


def _criar(client, dono: User, **over) -> dict:
    r = client.post("/api/v1/opportunities", json=_payload(**over), headers=_headers(dono))
    assert r.status_code == 201, r.text
    return r.json()


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def _usuario(session: Session, role: UserRole, first="Ana", last="Souza") -> User:
    user = User(
        email=f"{uuid.uuid4().hex[:10]}@teste.com",
        password_hash=hash_password("senha12345"),
        first_name=first,
        last_name=last,
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _atleta(
    session: Session,
    position: Position | None = Position.ATACANTE,
    birth_date: date | None = date(2008, 5, 1),  # 18 anos em AGORA
    first="Jeh",
) -> User:
    user = _usuario(session, UserRole.ATHLETE, first=first, last="Rodrigues")
    session.add(
        AthleteProfile(
            user_id=user.id, position=position, birth_date=birth_date, state="SP", city="Campinas"
        )
    )
    session.commit()
    return user


def test_apagar_peneira_apaga_inscricoes_em_cascata(session):
    clube = _usuario(session, UserRole.CLUB)
    atleta = _atleta(session)
    opp = Opportunity(
        organizer_id=clube.id,
        title="Peneira",
        description="Avaliação",
        mode=OpportunityMode.ONLINE,
        meeting_url="https://meet.example.com/x",
        event_at=AGORA + timedelta(days=10),
        registration_deadline=AGORA + timedelta(days=5),
    )
    session.add(opp)
    session.commit()
    session.add(OpportunityApplication(opportunity_id=opp.id, athlete_id=atleta.id))
    session.commit()

    session.execute(sa.delete(Opportunity).where(Opportunity.id == opp.id))
    session.commit()

    assert session.exec(select(OpportunityApplication)).all() == []


def test_inscricao_duplicada_viola_a_pk(session):
    clube = _usuario(session, UserRole.CLUB)
    atleta = _atleta(session)
    opp = Opportunity(
        organizer_id=clube.id,
        title="Peneira",
        description="Avaliação",
        mode=OpportunityMode.ONLINE,
        meeting_url="https://meet.example.com/x",
        event_at=AGORA + timedelta(days=10),
        registration_deadline=AGORA + timedelta(days=5),
    )
    session.add(opp)
    session.commit()
    session.add(OpportunityApplication(opportunity_id=opp.id, athlete_id=atleta.id))
    session.commit()

    session.add(OpportunityApplication(opportunity_id=opp.id, athlete_id=atleta.id))
    with pytest.raises(IntegrityError):
        session.commit()


# --- CRUD do organizador -----------------------------------------------------------

@pytest.mark.parametrize("role", [UserRole.CLUB, UserRole.SCOUT])
def test_clube_e_scout_criam_peneira(client, session, role):
    dono = _usuario(session, role, first="Guarani", last="FC")
    corpo = _criar(client, dono, positions=["MEIA", "ATACANTE", "MEIA"], state="sp")

    assert corpo["title"] == "Peneira Sub-17"
    assert corpo["state"] == "SP"
    assert corpo["positions"] == ["ATACANTE", "MEIA"]
    assert corpo["organizer"]["first_name"] == "Guarani"
    assert corpo["organizer"]["role"] == role.value
    assert corpo["is_open"] is True
    assert corpo["spots_left"] is None


def test_atleta_nao_cria_peneira(client, session):
    atleta = _atleta(session)
    r = client.post("/api/v1/opportunities", json=_payload(), headers=_headers(atleta))
    assert r.status_code == 403


def test_criar_valida_regras_de_negocio(client, session):
    dono = _usuario(session, UserRole.CLUB)
    r = client.post(
        "/api/v1/opportunities", json=_payload(address=None), headers=_headers(dono)
    )
    assert r.status_code == 422
    assert "endereço" in r.json()["detail"]


def test_criar_exige_data_com_fuso(client, session):
    dono = _usuario(session, UserRole.CLUB)
    r = client.post(
        "/api/v1/opportunities",
        json=_payload(event_at="2026-12-01T10:00:00"),
        headers=_headers(dono),
    )
    assert r.status_code == 422


def test_detalhe_inexistente_da_404(client, session):
    user = _atleta(session)
    r = client.get(f"/api/v1/opportunities/{uuid.uuid4()}", headers=_headers(user))
    assert r.status_code == 404


def test_link_online_so_aparece_para_o_dono(client, session):
    dono = _usuario(session, UserRole.SCOUT)
    opp = _criar(client, dono, mode="ONLINE", meeting_url="https://meet.example.com/abc")
    assert opp["meeting_url"] == "https://meet.example.com/abc"
    assert opp["state"] is None and opp["address"] is None

    outro = _atleta(session)
    r = client.get(f"/api/v1/opportunities/{opp['id']}", headers=_headers(outro))
    assert r.json()["meeting_url"] is None


def test_editar_peneira(client, session):
    dono = _usuario(session, UserRole.CLUB)
    opp = _criar(client, dono)
    r = client.patch(
        f"/api/v1/opportunities/{opp['id']}",
        json={"title": "Peneira Sub-20", "max_age": 20},
        headers=_headers(dono),
    )
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "Peneira Sub-20"
    assert r.json()["max_age"] == 20


def test_editar_valida_o_resultado_da_mescla(client, session):
    dono = _usuario(session, UserRole.CLUB)
    opp = _criar(client, dono)
    r = client.patch(
        f"/api/v1/opportunities/{opp['id']}", json={"mode": "ONLINE"}, headers=_headers(dono)
    )
    assert r.status_code == 422
    assert "link" in r.json()["detail"]


def test_quem_nao_e_dono_recebe_403(client, session):
    dono = _usuario(session, UserRole.CLUB)
    intruso = _usuario(session, UserRole.CLUB)
    opp = _criar(client, dono)
    url = f"/api/v1/opportunities/{opp['id']}"

    assert client.patch(url, json={"title": "Novo"}, headers=_headers(intruso)).status_code == 403
    assert client.post(f"{url}/cancel", headers=_headers(intruso)).status_code == 403
    assert client.delete(url, headers=_headers(intruso)).status_code == 403


def test_cancelar_e_idempotente_e_bloqueia_edicao(client, session):
    dono = _usuario(session, UserRole.CLUB)
    opp = _criar(client, dono)
    url = f"/api/v1/opportunities/{opp['id']}"

    r1 = client.post(f"{url}/cancel", headers=_headers(dono))
    r2 = client.post(f"{url}/cancel", headers=_headers(dono))
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["is_cancelled"] is True
    assert r1.json()["is_open"] is False
    assert r1.json()["cancelled_at"] == r2.json()["cancelled_at"]

    assert client.patch(url, json={"title": "Novo"}, headers=_headers(dono)).status_code == 409


def test_apagar_peneira(client, session):
    dono = _usuario(session, UserRole.CLUB)
    opp = _criar(client, dono)
    url = f"/api/v1/opportunities/{opp['id']}"

    assert client.delete(url, headers=_headers(dono)).status_code == 204
    assert client.get(url, headers=_headers(dono)).status_code == 404


# --- listagem ----------------------------------------------------------------------

def _titulos(client, user: User, query: str = "") -> list[str]:
    r = client.get(f"/api/v1/opportunities?{query}", headers=_headers(user))
    assert r.status_code == 200, r.text
    return [item["title"] for item in r.json()["items"]]


def test_lista_so_abertas_ordenadas_pela_data_do_evento(client, session):
    dono = _usuario(session, UserRole.CLUB)
    _criar(client, dono, title="Depois", event_at=(AGORA + timedelta(days=20)).isoformat())
    _criar(client, dono, title="Antes")
    cancelada = _criar(client, dono, title="Cancelada")
    client.post(f"/api/v1/opportunities/{cancelada['id']}/cancel", headers=_headers(dono))
    _criar(
        client,
        dono,
        title="Prazo vencido",
        registration_deadline=(AGORA - timedelta(days=1)).isoformat(),
    )

    assert _titulos(client, _atleta(session)) == ["Antes", "Depois"]


def test_lista_esconde_peneira_com_vagas_esgotadas(client, session):
    dono = _usuario(session, UserRole.CLUB)
    cheia = _criar(client, dono, title="Cheia", max_applications=1)
    atleta = _atleta(session)
    session.add(OpportunityApplication(opportunity_id=uuid.UUID(cheia["id"]), athlete_id=atleta.id))
    session.commit()

    assert _titulos(client, atleta) == []


def test_filtros_de_modo_uf_posicao_e_busca(client, session):
    dono = _usuario(session, UserRole.CLUB, first="Guarani", last="FC")
    _criar(client, dono, title="Presencial SP", positions=["GOLEIRO"])
    _criar(client, dono, title="Presencial RJ", state="RJ", city="Rio")
    _criar(client, dono, title="Online", mode="ONLINE", meeting_url="https://m.example.com/x")
    user = _atleta(session)

    assert _titulos(client, user, "mode=ONLINE") == ["Online"]
    assert _titulos(client, user, "state=rj") == ["Presencial RJ"]
    # posição: peneiras que aceitam a posição ou qualquer posição
    assert sorted(_titulos(client, user, "position=ATACANTE")) == ["Online", "Presencial RJ"]
    assert _titulos(client, user, "q=online") == ["Online"]
    assert len(_titulos(client, user, "q=guarani")) == 3


def test_filtro_elegiveis_usa_idade_e_posicao_do_atleta(client, session):
    dono = _usuario(session, UserRole.CLUB)
    _criar(client, dono, title="Livre")
    _criar(client, dono, title="Sub-17", max_age=17)
    _criar(client, dono, title="Goleiros", positions=["GOLEIRO"])
    _criar(client, dono, title="Atacantes 16-20", min_age=16, max_age=20, positions=["ATACANTE"])

    atleta = _atleta(session)  # 18 anos, atacante
    assert sorted(_titulos(client, atleta, "eligible=true")) == ["Atacantes 16-20", "Livre"]

    sem_dados = _atleta(session, position=None, birth_date=None)
    assert _titulos(client, sem_dados, "eligible=true") == ["Livre"]


def test_filtro_elegiveis_e_so_para_atleta(client, session):
    clube = _usuario(session, UserRole.CLUB)
    r = client.get("/api/v1/opportunities?eligible=true", headers=_headers(clube))
    assert r.status_code == 422


def test_paginacao_por_cursor_nao_repete_nem_pula(client, session):
    dono = _usuario(session, UserRole.CLUB)
    for i in range(5):
        _criar(client, dono, title=f"Pen{i}", event_at=(AGORA + timedelta(days=10 + i)).isoformat())
    user = _atleta(session)

    vistos, cursor = [], None
    while True:
        query = "limit=2" + (f"&cursor={cursor}" if cursor else "")
        corpo = client.get(f"/api/v1/opportunities?{query}", headers=_headers(user)).json()
        vistos += [item["title"] for item in corpo["items"]]
        cursor = corpo["next_cursor"]
        if not cursor:
            break

    assert vistos == ["Pen0", "Pen1", "Pen2", "Pen3", "Pen4"]


def test_cursor_invalido_da_422(client, session):
    r = client.get("/api/v1/opportunities?cursor=lixo", headers=_headers(_atleta(session)))
    assert r.status_code == 422

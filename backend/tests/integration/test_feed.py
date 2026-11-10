"""
Feed de clipes publicados:
  POST   /api/v1/clips/{clip_id}/publish
  DELETE /api/v1/clips/{clip_id}/publish
  GET    /api/v1/feed
  POST   /api/v1/feed/clips/{clip_id}/like
  DELETE /api/v1/feed/clips/{clip_id}/like
"""
import subprocess
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.clips.models import Clip, ClipStatus, ProcessingJob, Video
from app.modules.feed.router import get_today
from app.modules.identity.models import User, UserRole
from app.modules.profiles.models import AthleteProfile, AthleteStatus, Position

from tests.integration.conftest import BACKEND_DIR, url_validada_para_migracao

HOJE = date(2026, 10, 27)


@pytest.fixture(autouse=True)
def _hoje_fixo():
    app.dependency_overrides[get_today] = lambda: (lambda: HOJE)
    yield
    app.dependency_overrides.pop(get_today, None)


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def _usuario(session: Session, role: UserRole = UserRole.ATHLETE, first="Jeh", last="Rodrigues") -> User:
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
    first="Jeh",
    last="Rodrigues",
    position=Position.ATACANTE,
    birth_date=date(2007, 3, 10),
    status=AthleteStatus.DISPONIVEL,
) -> User:
    user = _usuario(session, UserRole.ATHLETE, first, last)
    session.add(
        AthleteProfile(
            user_id=user.id,
            position=position,
            birth_date=birth_date,
            state="SP",
            city="Campinas",
            status=status,
        )
    )
    session.commit()
    return user


def _clipe(
    session: Session,
    dono: User,
    status: str = ClipStatus.TEMPORARY,
    published_at: datetime | None = None,
    com_arquivo: bool = True,
) -> Clip:
    video = Video(user_id=dono.id, original_filename="jogo.mp4", storage_path="videos/jogo.mp4")
    session.add(video)
    session.commit()
    job = ProcessingJob(video_id=video.id, target_number=10, status="COMPLETED")
    session.add(job)
    session.commit()
    clip = Clip(
        job_id=job.id,
        storage_path=f"clips/{job.id}/clip_1.mp4" if com_arquivo else None,
        status=status,
        start_timestamp=10.0,
        end_timestamp=17.5,
        published_at=published_at,
    )
    session.add(clip)
    session.commit()
    session.refresh(clip)
    return clip


def _publicado(session, dono, minutos_atras: int = 0) -> Clip:
    quando = datetime(2026, 10, 27, 12, 0) - timedelta(minutes=minutos_atras)
    return _clipe(session, dono, ClipStatus.PUBLISHED, published_at=quando)


# --- publicar / despublicar ------------------------------------------------------------


def test_atleta_publica_o_proprio_clipe(client, session):
    atleta = _atleta(session)
    clip = _clipe(session, atleta)

    resp = client.post(f"/api/v1/clips/{clip.id}/publish", headers=_headers(atleta))

    assert resp.status_code == 200
    assert resp.json()["status"] == "PUBLISHED"
    assert resp.json()["published_at"] is not None
    session.refresh(clip)
    assert clip.status == ClipStatus.PUBLISHED


def test_publicar_de_novo_mantem_a_data_original(client, session):
    atleta = _atleta(session)
    clip = _clipe(session, atleta)
    primeira = client.post(f"/api/v1/clips/{clip.id}/publish", headers=_headers(atleta)).json()

    segunda = client.post(f"/api/v1/clips/{clip.id}/publish", headers=_headers(atleta)).json()

    assert segunda["published_at"] == primeira["published_at"]


def test_nao_publica_clipe_de_outro_usuario(client, session):
    dono = _atleta(session)
    outro = _atleta(session, first="Outro")
    clip = _clipe(session, dono)

    resp = client.post(f"/api/v1/clips/{clip.id}/publish", headers=_headers(outro))

    assert resp.status_code == 403


def test_scout_nao_publica(client, session):
    scout = _usuario(session, UserRole.SCOUT)
    clip = _clipe(session, scout)

    resp = client.post(f"/api/v1/clips/{clip.id}/publish", headers=_headers(scout))

    assert resp.status_code == 403


def test_clipe_expirado_nao_pode_ser_publicado(client, session):
    atleta = _atleta(session)
    clip = _clipe(session, atleta, ClipStatus.DELETED, com_arquivo=False)

    resp = client.post(f"/api/v1/clips/{clip.id}/publish", headers=_headers(atleta))

    assert resp.status_code == 409


def test_publicar_clipe_inexistente_e_404(client, session):
    atleta = _atleta(session)

    resp = client.post(f"/api/v1/clips/{uuid.uuid4()}/publish", headers=_headers(atleta))

    assert resp.status_code == 404


def test_despublicar_volta_para_temporary(client, session):
    atleta = _atleta(session)
    clip = _publicado(session, atleta)

    resp = client.delete(f"/api/v1/clips/{clip.id}/publish", headers=_headers(atleta))

    assert resp.status_code == 200
    assert resp.json() == {"id": str(clip.id), "status": "TEMPORARY", "published_at": None}


def test_historico_expoe_published_at(client, session):
    atleta = _atleta(session)
    _publicado(session, atleta)

    resp = client.get("/api/v1/clips/", headers=_headers(atleta))

    assert resp.json()[0]["clips"][0]["published_at"] is not None


# --- GET /feed -------------------------------------------------------------------------


def test_feed_traz_so_clipes_publicados_com_dados_do_atleta(client, session):
    atleta = _atleta(session)
    publicado = _publicado(session, atleta)
    _clipe(session, atleta)  # temporario: fora do feed
    scout = _usuario(session, UserRole.SCOUT)

    resp = client.get("/api/v1/feed", headers=_headers(scout))

    assert resp.status_code == 200
    corpo = resp.json()
    assert [item["id"] for item in corpo["items"]] == [str(publicado.id)]
    item = corpo["items"][0]
    assert item["file_url"] == f"/uploads/clips/{publicado.job_id}/clip_1.mp4"
    assert item["duration_seconds"] == 7.5
    assert item["like_count"] == 0
    assert item["liked_by_me"] is False
    assert item["athlete"] == {
        "user_id": str(atleta.id),
        "first_name": "Jeh",
        "last_name": "Rodrigues",
        "avatar_url": None,
        "position": "ATACANTE",
        "age": 19,
        "city": "Campinas",
        "state": "SP",
        "status": "DISPONIVEL",
    }
    assert corpo["next_cursor"] is None


def test_feed_exige_login(client):
    assert client.get("/api/v1/feed").status_code == 401


def test_feed_ordena_do_mais_novo_para_o_mais_antigo(client, session):
    atleta = _atleta(session)
    antigo = _publicado(session, atleta, minutos_atras=60)
    novo = _publicado(session, atleta, minutos_atras=1)

    corpo = client.get("/api/v1/feed", headers=_headers(atleta)).json()

    assert [i["id"] for i in corpo["items"]] == [str(novo.id), str(antigo.id)]


def test_feed_pagina_por_cursor_sem_repetir_nem_pular(client, session):
    atleta = _atleta(session)
    clipes = [_publicado(session, atleta, minutos_atras=m) for m in range(5)]
    vistos = []
    cursor = None

    for _ in range(3):
        params = {"limit": 2, **({"cursor": cursor} if cursor else {})}
        corpo = client.get("/api/v1/feed", params=params, headers=_headers(atleta)).json()
        vistos += [i["id"] for i in corpo["items"]]
        cursor = corpo["next_cursor"]

    assert vistos == [str(c.id) for c in clipes]
    assert cursor is None


def test_cursor_invalido_e_422(client, session):
    atleta = _atleta(session)

    resp = client.get("/api/v1/feed", params={"cursor": "lixo"}, headers=_headers(atleta))

    assert resp.status_code == 422


@pytest.mark.parametrize(
    "params, esperados",
    [
        ({"position": "GOLEIRO"}, {"goleiro"}),
        ({"status": "DISPONIVEL"}, {"atacante", "goleiro"}),
        ({"max_age": 19}, {"atacante"}),  # Sub-20
        ({"min_age": 20}, {"goleiro", "meia"}),
        ({"q": "silva"}, {"goleiro"}),
        ({"q": "Ana Lu"}, {"meia"}),
        ({"position": "ATACANTE", "max_age": 15}, set()),
    ],
)
def test_feed_filtra(client, session, params, esperados):
    atletas = {
        "atacante": _atleta(session, "Jeh", "Rodrigues", Position.ATACANTE, date(2007, 3, 10)),
        "goleiro": _atleta(session, "Caio", "Silva", Position.GOLEIRO, date(2000, 1, 1)),
        "meia": _atleta(
            session, "Ana", "Lucia", Position.MEIA, date(1998, 5, 5), AthleteStatus.CONTRATADO
        ),
    }
    clipe_de = {nome: _publicado(session, a).id for nome, a in atletas.items()}

    corpo = client.get("/api/v1/feed", params=params, headers=_headers(atletas["meia"])).json()

    ids = {i["id"] for i in corpo["items"]}
    assert ids == {str(clipe_de[nome]) for nome in esperados}


def test_busca_trata_porcentagem_como_texto(client, session):
    atleta = _atleta(session)
    _publicado(session, atleta)

    corpo = client.get("/api/v1/feed", params={"q": "%"}, headers=_headers(atleta)).json()

    assert corpo["items"] == []


def test_min_age_maior_que_max_age_e_422(client, session):
    atleta = _atleta(session)

    resp = client.get(
        "/api/v1/feed", params={"min_age": 20, "max_age": 15}, headers=_headers(atleta)
    )

    assert resp.status_code == 422


# --- curtidas --------------------------------------------------------------------------


def test_curtir_e_descurtir(client, session):
    atleta = _atleta(session)
    clip = _publicado(session, atleta)
    scout = _usuario(session, UserRole.SCOUT)

    curtiu = client.post(f"/api/v1/feed/clips/{clip.id}/like", headers=_headers(scout))
    feed = client.get("/api/v1/feed", headers=_headers(scout)).json()
    descurtiu = client.delete(f"/api/v1/feed/clips/{clip.id}/like", headers=_headers(scout))

    assert curtiu.status_code == 200
    assert curtiu.json() == {"clip_id": str(clip.id), "like_count": 1, "liked_by_me": True}
    assert feed["items"][0]["like_count"] == 1
    assert feed["items"][0]["liked_by_me"] is True
    assert descurtiu.json() == {"clip_id": str(clip.id), "like_count": 0, "liked_by_me": False}


def test_curtir_duas_vezes_conta_uma(client, session):
    atleta = _atleta(session)
    clip = _publicado(session, atleta)

    client.post(f"/api/v1/feed/clips/{clip.id}/like", headers=_headers(atleta))
    resp = client.post(f"/api/v1/feed/clips/{clip.id}/like", headers=_headers(atleta))

    assert resp.json()["like_count"] == 1


def test_curtida_de_outro_usuario_nao_marca_liked_by_me(client, session):
    atleta = _atleta(session)
    clip = _publicado(session, atleta)
    scout = _usuario(session, UserRole.SCOUT)
    client.post(f"/api/v1/feed/clips/{clip.id}/like", headers=_headers(scout))

    item = client.get("/api/v1/feed", headers=_headers(atleta)).json()["items"][0]

    assert item["like_count"] == 1
    assert item["liked_by_me"] is False


def test_nao_curte_clipe_nao_publicado(client, session):
    atleta = _atleta(session)
    clip = _clipe(session, atleta)

    resp = client.post(f"/api/v1/feed/clips/{clip.id}/like", headers=_headers(atleta))

    assert resp.status_code == 404


def test_apagar_clipe_curtido_leva_as_curtidas_junto(client, session):
    atleta = _atleta(session)
    clip = _publicado(session, atleta)
    client.post(f"/api/v1/feed/clips/{clip.id}/like", headers=_headers(atleta))

    resp = client.delete(f"/api/v1/clips/{clip.id}", headers=_headers(atleta))

    assert resp.status_code == 204


# --- schema ----------------------------------------------------------------------------


def test_models_e_migracoes_nao_divergem(engine):
    """`alembic check` falha se um model ganhou coluna/indice sem migracao."""
    url = url_validada_para_migracao(engine.url)
    resultado = subprocess.run(
        ["alembic", "-x", f"db_url={url}", "check"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr

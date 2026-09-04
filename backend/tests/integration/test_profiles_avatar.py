"""
Integração do avatar (§4.1 da spec): upload, troca e remoção nos três papéis.

O `StorageBackend` é substituído por um enraizado em `tmp_path`. Sem isso cada rodada
da suíte deixaria arquivos em `backend/uploads/avatars/`, e o teste de "trocar avatar
apaga o anterior" passaria a depender do lixo da rodada passada.
"""
import pytest
from sqlmodel import select

from app.core.security import create_access_token, hash_password
from app.core.storage import LocalStorageBackend, get_storage
from app.main import app
from app.modules.identity.models import User, UserRole
from app.modules.profiles.models import AthleteProfile, ClubProfile, ScoutProfile

# O conteúdo não importa: a validação olha o content-type declarado, não os bytes
# (decisão E3 -- nenhum processamento de imagem nesta fatia).
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64

DOIS_MB = 2 * 1024 * 1024


def _envio(conteudo: bytes, nome: str, tipo: str) -> dict:
    return {"file": (nome, conteudo, tipo)}


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def _cria_usuario(session, email: str, role: UserRole) -> User:
    user = User(
        email=email,
        password_hash=hash_password("senha12345"),
        first_name="Fulano",
        last_name="de Tal",
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def uploads(tmp_path):
    """Raiz de uploads descartável, injetada no lugar do backend padrão do processo."""
    raiz = tmp_path / "uploads"
    app.dependency_overrides[get_storage] = lambda: LocalStorageBackend(root=raiz)
    yield raiz
    app.dependency_overrides.pop(get_storage, None)


@pytest.fixture
def perfil(session, usuario) -> AthleteProfile:
    p = AthleteProfile(user_id=usuario.id)
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


@pytest.fixture
def usuario_scout(session) -> User:
    return _cria_usuario(session, "scout.avatar@teste.com", UserRole.SCOUT)


@pytest.fixture
def perfil_scout(session, usuario_scout) -> ScoutProfile:
    p = ScoutProfile(user_id=usuario_scout.id)
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


@pytest.fixture
def usuario_clube(session) -> User:
    return _cria_usuario(session, "clube.avatar@teste.com", UserRole.CLUB)


@pytest.fixture
def perfil_clube(session, usuario_clube) -> ClubProfile:
    p = ClubProfile(user_id=usuario_clube.id)
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def test_upload_grava_o_arquivo_e_devolve_o_perfil(
    client, auth_headers, usuario, perfil, uploads
):
    resposta = client.post(
        "/api/v1/profiles/me/avatar",
        headers=auth_headers,
        files=_envio(JPEG, "foto.jpg", "image/jpeg"),
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["role"] == "ATHLETE"
    assert corpo["profile"]["avatar_url"] == f"/uploads/avatars/{usuario.id}.jpg"
    assert (uploads / "avatars" / f"{usuario.id}.jpg").read_bytes() == JPEG


def test_upload_devolve_birth_date_no_perfil_de_atleta(
    client, auth_headers, usuario, perfil, uploads
):
    """
    O upload devolve o mesmo formato de `GET /profiles/me` -- se um carrega `birth_date`
    do dono, o outro tambem precisa carregar.
    """
    resposta = client.post(
        "/api/v1/profiles/me/avatar",
        headers=auth_headers,
        files=_envio(JPEG, "foto.jpg", "image/jpeg"),
    )

    assert resposta.status_code == 200
    assert "birth_date" in resposta.json()["profile"]


def test_upload_reflete_no_get_me_seguinte(client, auth_headers, usuario, perfil, uploads):
    """Prova o commit do handler: a leitura seguinte usa outra Session (ver conftest)."""
    client.post(
        "/api/v1/profiles/me/avatar",
        headers=auth_headers,
        files=_envio(PNG, "foto.png", "image/png"),
    )

    corpo = client.get("/api/v1/profiles/me", headers=auth_headers).json()
    assert corpo["profile"]["avatar_url"] == f"/uploads/avatars/{usuario.id}.png"


def test_upload_de_tipo_invalido_devolve_422(client, auth_headers, perfil, uploads):
    resposta = client.post(
        "/api/v1/profiles/me/avatar",
        headers=auth_headers,
        files=_envio(b"%PDF-1.4", "curriculo.pdf", "application/pdf"),
    )

    assert resposta.status_code == 422
    assert not (uploads / "avatars").exists()


def test_upload_acima_de_2mb_devolve_422(client, auth_headers, usuario, perfil, uploads):
    gorda = b"\xff\xd8\xff\xe0" + b"0" * DOIS_MB

    resposta = client.post(
        "/api/v1/profiles/me/avatar",
        headers=auth_headers,
        files=_envio(gorda, "gorda.jpg", "image/jpeg"),
    )

    assert resposta.status_code == 422
    assert not (uploads / "avatars" / f"{usuario.id}.jpg").exists()


def test_upload_no_limite_de_2mb_e_aceito(client, auth_headers, usuario, perfil, uploads):
    """A borda vale: 2 MB exatos passam, 2 MB + 1 byte não (o teste acima)."""
    resposta = client.post(
        "/api/v1/profiles/me/avatar",
        headers=auth_headers,
        files=_envio(b"0" * DOIS_MB, "no_limite.jpg", "image/jpeg"),
    )

    assert resposta.status_code == 200
    assert (uploads / "avatars" / f"{usuario.id}.jpg").stat().st_size == DOIS_MB


def test_upload_sem_jwt_devolve_401(client, perfil, uploads):
    resposta = client.post(
        "/api/v1/profiles/me/avatar", files=_envio(JPEG, "foto.jpg", "image/jpeg")
    )

    assert resposta.status_code == 401


def test_upload_sem_perfil_do_papel_devolve_404_e_nao_grava_nada(
    client, usuario_scout, uploads
):
    """Sem linha em `scout_profiles`: 404 antes de qualquer byte ir para o disco."""
    resposta = client.post(
        "/api/v1/profiles/me/avatar",
        headers=_headers(usuario_scout),
        files=_envio(JPEG, "foto.jpg", "image/jpeg"),
    )

    assert resposta.status_code == 404
    assert not (uploads / "avatars").exists()


# ---------------------------------------------------------------------------
# Troca: o arquivo anterior não pode sobrar no disco (§4.1)
# ---------------------------------------------------------------------------

def test_trocar_avatar_apaga_o_arquivo_anterior(
    client, auth_headers, usuario, perfil, uploads
):
    client.post(
        "/api/v1/profiles/me/avatar",
        headers=auth_headers,
        files=_envio(PNG, "antiga.png", "image/png"),
    )
    anterior = uploads / "avatars" / f"{usuario.id}.png"
    assert anterior.exists()

    resposta = client.post(
        "/api/v1/profiles/me/avatar",
        headers=auth_headers,
        files=_envio(JPEG, "nova.jpg", "image/jpeg"),
    )

    assert resposta.status_code == 200
    novo = uploads / "avatars" / f"{usuario.id}.jpg"
    assert novo.read_bytes() == JPEG
    assert not anterior.exists(), "o avatar antigo ficou órfão no disco"


def test_trocar_avatar_pela_mesma_extensao_mantem_o_arquivo_novo(
    client, auth_headers, usuario, perfil, uploads
):
    """
    Mesma extensão reaproveita a chave: o `delete` do anterior apagaria o arquivo
    recém-gravado se não olhasse que o caminho não mudou.
    """
    client.post(
        "/api/v1/profiles/me/avatar",
        headers=auth_headers,
        files=_envio(JPEG, "antiga.jpg", "image/jpeg"),
    )
    client.post(
        "/api/v1/profiles/me/avatar",
        headers=auth_headers,
        files=_envio(b"\xff\xd8\xff\xe0nova", "nova.jpg", "image/jpeg"),
    )

    arquivo = uploads / "avatars" / f"{usuario.id}.jpg"
    assert arquivo.read_bytes() == b"\xff\xd8\xff\xe0nova"


# ---------------------------------------------------------------------------
# Remoção
# ---------------------------------------------------------------------------

def test_delete_remove_o_arquivo_e_zera_o_campo(
    client, auth_headers, usuario, perfil, uploads
):
    client.post(
        "/api/v1/profiles/me/avatar",
        headers=auth_headers,
        files=_envio(JPEG, "foto.jpg", "image/jpeg"),
    )
    arquivo = uploads / "avatars" / f"{usuario.id}.jpg"
    assert arquivo.exists()

    resposta = client.delete("/api/v1/profiles/me/avatar", headers=auth_headers)

    assert resposta.status_code == 204
    assert not arquivo.exists()
    corpo = client.get("/api/v1/profiles/me", headers=auth_headers).json()
    assert corpo["profile"]["avatar_url"] is None
    assert "birth_date" in corpo["profile"]


def test_delete_sem_avatar_e_idempotente(client, auth_headers, perfil, uploads):
    primeira = client.delete("/api/v1/profiles/me/avatar", headers=auth_headers)
    segunda = client.delete("/api/v1/profiles/me/avatar", headers=auth_headers)

    assert primeira.status_code == 204
    assert segunda.status_code == 204


def test_delete_sem_perfil_do_papel_devolve_404(client, usuario_scout, uploads):
    resposta = client.delete(
        "/api/v1/profiles/me/avatar", headers=_headers(usuario_scout)
    )

    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# O papel vem do JWT (decisão E4): um endpoint, três tabelas
# ---------------------------------------------------------------------------

def test_upload_de_scout_grava_no_perfil_de_scout(
    client, session, usuario_scout, perfil_scout, uploads
):
    resposta = client.post(
        "/api/v1/profiles/me/avatar",
        headers=_headers(usuario_scout),
        files=_envio(PNG, "foto.png", "image/png"),
    )

    assert resposta.status_code == 200
    assert resposta.json()["role"] == "SCOUT"

    session.expire_all()
    gravado = session.exec(
        select(ScoutProfile).where(ScoutProfile.user_id == usuario_scout.id)
    ).one()
    assert gravado.avatar_path == f"/uploads/avatars/{usuario_scout.id}.png"


def test_upload_de_clube_grava_no_perfil_de_clube(
    client, session, usuario_clube, perfil_clube, uploads
):
    resposta = client.post(
        "/api/v1/profiles/me/avatar",
        headers=_headers(usuario_clube),
        files=_envio(JPEG, "foto.jpg", "image/jpeg"),
    )

    assert resposta.status_code == 200
    assert resposta.json()["role"] == "CLUB"

    session.expire_all()
    gravado = session.exec(
        select(ClubProfile).where(ClubProfile.user_id == usuario_clube.id)
    ).one()
    assert gravado.avatar_path == f"/uploads/avatars/{usuario_clube.id}.jpg"


def test_upload_de_scout_nao_toca_no_perfil_do_atleta(
    client, session, usuario, perfil, usuario_scout, perfil_scout, uploads
):
    client.post(
        "/api/v1/profiles/me/avatar",
        headers=_headers(usuario_scout),
        files=_envio(PNG, "foto.png", "image/png"),
    )

    session.expire_all()
    do_atleta = session.exec(
        select(AthleteProfile).where(AthleteProfile.user_id == usuario.id)
    ).one()
    assert do_atleta.avatar_path is None

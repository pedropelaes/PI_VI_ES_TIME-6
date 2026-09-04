"""
Regras do avatar sem HTTP e sem banco: só o `StorageBackend` em `tmp_path`.

Cobre os caminhos que a suíte de integração não alcança -- em especial valores de
`avatar_path` que não vieram deste endpoint, já que a coluna existe desde antes dele.
"""
import uuid

import pytest

from app.core.exceptions import ValidationError
from app.core.storage import LocalStorageBackend
from app.modules.profiles.service import TAMANHO_MAXIMO_DE_AVATAR, AvatarService


@pytest.fixture
def avatares(tmp_path) -> AvatarService:
    return AvatarService(LocalStorageBackend(root=tmp_path))


def test_salvar_devolve_a_url_publica_e_grava_pela_chave(avatares, tmp_path):
    user_id = uuid.uuid4()

    url = avatares.salvar(user_id, b"bytes", "image/webp")

    assert url == f"/uploads/avatars/{user_id}.webp"
    assert (tmp_path / "avatars" / f"{user_id}.webp").read_bytes() == b"bytes"


def test_content_type_com_parametro_e_aceito(avatares):
    """Navegadores mandam `image/jpeg; charset=...` de vez em quando."""
    url = avatares.salvar(uuid.uuid4(), b"bytes", "image/JPEG; charset=binary")

    assert url.endswith(".jpg")


@pytest.mark.parametrize("tipo", ["image/gif", "application/pdf", "text/plain", None, ""])
def test_tipo_fora_da_lista_e_recusado(avatares, tipo):
    with pytest.raises(ValidationError):
        avatares.salvar(uuid.uuid4(), b"bytes", tipo)


def test_um_byte_acima_do_limite_e_recusado(avatares):
    with pytest.raises(ValidationError):
        avatares.salvar(uuid.uuid4(), b"0" * (TAMANHO_MAXIMO_DE_AVATAR + 1), "image/png")


def test_remover_apaga_o_arquivo_da_url(avatares, tmp_path):
    user_id = uuid.uuid4()
    url = avatares.salvar(user_id, b"bytes", "image/png")

    avatares.remover(url)

    assert not (tmp_path / "avatars" / f"{user_id}.png").exists()


def test_remover_sem_avatar_e_no_op(avatares):
    avatares.remover(None)


def test_remover_valor_fora_da_raiz_de_uploads_nao_apaga_nada(avatares, tmp_path):
    """
    `avatar_path` é anterior a este endpoint e pode conter qualquer texto legado.
    Um valor que não é uma URL de uploads não pode virar um `unlink` em caminho
    arbitrário -- inclusive um `..` que escaparia da raiz.
    """
    alvo = tmp_path / "importante.txt"
    alvo.write_text("nao me apague")

    avatares.remover("avatars/legado.png")
    avatares.remover("/etc/passwd")
    avatares.remover("/uploads/../importante.txt")
    avatares.remover("/uploads/")

    assert alvo.exists()

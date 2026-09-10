"""
Testes unitarios dos services de scout e clube: sem banco, sem HTTP.

Mesmo loop rapido do `test_profiles_service.py` -- o repositorio e uma fake em
dicionario, entao estes testes precisam passar com o `postgres-test` desligado.
"""
import uuid
from dataclasses import replace
from typing import Any, Optional

import pytest

from app.core.exceptions import NotFoundError
from app.modules.identity.models import UserRole
from app.modules.profiles.models import ClubCategory
from app.modules.profiles.repository import ClubProfileRecord, ScoutProfileRecord
from app.modules.profiles.service import (
    ClubProfilesService,
    ScoutProfilesService,
    provision_profile,
)

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OUTRO_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def um_scout(**overrides: Any) -> ScoutProfileRecord:
    base = dict(
        user_id=USER_ID,
        first_name="Ana",
        last_name="Souza",
        organization="Cruzeiro",
        credential="CBF-1234",
        state="MG",
        city="Belo Horizonte",
        bio=None,
        avatar_path=None,
    )
    base.update(overrides)
    return ScoutProfileRecord(**base)


def um_clube(**overrides: Any) -> ClubProfileRecord:
    base = dict(
        user_id=USER_ID,
        first_name="Clube",
        last_name="Atletico",
        legal_name="Clube Atletico LTDA",
        cnpj="12345678000199",
        categories=[ClubCategory.SUB_17.value],
        state="SP",
        city="Santos",
        bio=None,
        avatar_path=None,
    )
    base.update(overrides)
    return ClubProfileRecord(**base)


class FakeRepository:
    """Espelha o contrato dos repositorios SQL: None quando o id nao bate, merge no update."""

    def __init__(self, record: Optional[Any] = None):
        self.record = record
        self.ultima_atualizacao: Optional[dict[str, Any]] = None

    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[Any]:
        if self.record is None or self.record.user_id != user_id:
            return None
        return self.record

    def update(self, user_id: uuid.UUID, changes: dict[str, Any]) -> Optional[Any]:
        if self.record is None or self.record.user_id != user_id:
            return None
        self.ultima_atualizacao = changes
        self.record = replace(self.record, **changes)
        return self.record

    def create(self, user_id: uuid.UUID) -> None:  # pragma: no cover - nao usado aqui
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Scout
# ---------------------------------------------------------------------------

def test_scout_devolve_os_campos_do_papel():
    perfil = ScoutProfilesService(FakeRepository(um_scout())).get_scout_profile(USER_ID)

    assert perfil.organization == "Cruzeiro"
    assert perfil.credential == "CBF-1234"
    assert perfil.city == "Belo Horizonte"
    assert perfil.first_name == "Ana"


def test_scout_inexistente_levanta_not_found():
    with pytest.raises(NotFoundError):
        ScoutProfilesService(FakeRepository(None)).get_scout_profile(USER_ID)


def test_atualizacao_de_scout_so_repassa_os_campos_enviados():
    repo = FakeRepository(um_scout())
    ScoutProfilesService(repo).update_scout_profile(USER_ID, {"city": "Contagem"})

    assert repo.ultima_atualizacao == {"city": "Contagem"}


def test_atualizacao_de_scout_preserva_campos_nao_enviados():
    service = ScoutProfilesService(FakeRepository(um_scout()))
    perfil = service.update_scout_profile(USER_ID, {"city": "Contagem"})

    assert perfil.city == "Contagem"
    assert perfil.organization == "Cruzeiro"


def test_atualizar_scout_inexistente_levanta_not_found():
    with pytest.raises(NotFoundError):
        ScoutProfilesService(FakeRepository(None)).update_scout_profile(
            USER_ID, {"city": "Contagem"}
        )


def test_atualizar_scout_com_id_diferente_do_registro_levanta_not_found():
    with pytest.raises(NotFoundError):
        ScoutProfilesService(FakeRepository(um_scout())).update_scout_profile(
            OUTRO_ID, {"city": "Contagem"}
        )


# ---------------------------------------------------------------------------
# Clube
# ---------------------------------------------------------------------------

def test_clube_devolve_os_campos_do_papel():
    perfil = ClubProfilesService(FakeRepository(um_clube())).get_club_profile(USER_ID)

    assert perfil.legal_name == "Clube Atletico LTDA"
    assert perfil.cnpj == "12345678000199"
    assert perfil.categories == ["SUB_17"]


def test_clube_inexistente_levanta_not_found():
    with pytest.raises(NotFoundError):
        ClubProfilesService(FakeRepository(None)).get_club_profile(USER_ID)


def test_atualizacao_de_clube_troca_a_lista_de_categorias_inteira():
    service = ClubProfilesService(FakeRepository(um_clube()))
    perfil = service.update_club_profile(
        USER_ID, {"categories": ["SUB_20", "PROFISSIONAL"]}
    )

    assert perfil.categories == ["SUB_20", "PROFISSIONAL"]
    assert perfil.legal_name == "Clube Atletico LTDA"


def test_atualizar_clube_inexistente_levanta_not_found():
    with pytest.raises(NotFoundError):
        ClubProfilesService(FakeRepository(None)).update_club_profile(
            USER_ID, {"city": "Santos"}
        )


def test_atualizar_clube_com_id_diferente_do_registro_levanta_not_found():
    with pytest.raises(NotFoundError):
        ClubProfilesService(FakeRepository(um_clube())).update_club_profile(
            OUTRO_ID, {"city": "Santos"}
        )


# ---------------------------------------------------------------------------
# provision_profile -- o ponto de entrada D3 usado pelo `register`
# ---------------------------------------------------------------------------

class SessaoFalsa:
    """
    Session minima: registra o que foi adicionado sem tocar em banco.

    `provision_profile` so precisa de `add` + `flush`, entao da para provar a escolha da
    tabela por papel no loop rapido, sem Postgres no ar.
    """

    def __init__(self) -> None:
        self.adicionados: list[Any] = []
        self.flushes = 0

    def add(self, obj: Any) -> None:
        self.adicionados.append(obj)

    def flush(self) -> None:
        self.flushes += 1

    def commit(self) -> None:
        raise AssertionError(
            "provision_profile nao pode commitar: a transacao e do chamador (`register`)."
        )


@pytest.mark.parametrize(
    "role, tabela",
    [
        (UserRole.ATHLETE, "athlete_profiles"),
        (UserRole.SCOUT, "scout_profiles"),
        (UserRole.CLUB, "club_profiles"),
    ],
)
def test_provision_profile_escolhe_a_tabela_do_papel(role, tabela):
    sessao = SessaoFalsa()

    provision_profile(sessao, USER_ID, role)

    assert len(sessao.adicionados) == 1
    perfil = sessao.adicionados[0]
    assert perfil.__tablename__ == tabela
    assert perfil.user_id == USER_ID


def test_provision_profile_nao_commita():
    """Quem chama (`register`) e dono da transacao -- o provision so faz flush."""
    sessao = SessaoFalsa()

    provision_profile(sessao, USER_ID, UserRole.SCOUT)

    # `SessaoFalsa.commit` estoura AssertionError: chegar ate aqui ja prova que nao
    # houve commit. O flush e o que torna a criacao visivel para o resto da transacao.
    assert sessao.flushes == 1

"""
Testes unitarios do service: sem banco, sem HTTP. O repository e uma fake em dicionario.
Este e o loop rapido do TDD -- roda em milissegundos.
"""
import uuid
from datetime import date
from typing import Any, Optional

import pytest

from app.core.exceptions import NotFoundError
from app.modules.profiles.models import AthleteStatus, DominantFoot, Position
from app.modules.profiles.repository import AthleteProfileRecord
from app.modules.profiles.service import ProfilesService

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def um_record(**overrides: Any) -> AthleteProfileRecord:
    base = dict(
        user_id=USER_ID,
        first_name="Jeh",
        last_name="Rodrigues",
        position=Position.ATACANTE,
        birth_date=date(2007, 3, 10),
        height_cm=178,
        dominant_foot=DominantFoot.DESTRO,
        state="SP",
        city="Campinas",
        current_club=None,
        bio=None,
        avatar_path=None,
        status=AthleteStatus.DISPONIVEL,
    )
    base.update(overrides)
    return AthleteProfileRecord(**base)


class FakeRepository:
    def __init__(self, record: Optional[AthleteProfileRecord] = None, clips: int = 0):
        self.record = record
        self.clips = clips
        self.ultima_atualizacao: Optional[dict[str, Any]] = None

    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[AthleteProfileRecord]:
        if self.record is None or self.record.user_id != user_id:
            return None
        return self.record

    def count_clips(self, user_id: uuid.UUID) -> int:
        return self.clips

    def update(
        self, user_id: uuid.UUID, changes: dict[str, Any]
    ) -> Optional[AthleteProfileRecord]:
        if self.record is None:
            return None
        self.ultima_atualizacao = changes
        self.record = um_record(**changes)
        return self.record


def test_calcula_idade_a_partir_da_data_de_nascimento():
    service = ProfilesService(
        FakeRepository(um_record(birth_date=date(2007, 3, 10))),
        hoje=lambda: date(2026, 9, 2),
    )
    assert service.get_athlete_profile(USER_ID).age == 19


def test_idade_desconta_aniversario_ainda_nao_ocorrido_no_ano():
    service = ProfilesService(
        FakeRepository(um_record(birth_date=date(2007, 12, 31))),
        hoje=lambda: date(2026, 9, 2),
    )
    assert service.get_athlete_profile(USER_ID).age == 18


def test_idade_no_proprio_dia_do_aniversario():
    service = ProfilesService(
        FakeRepository(um_record(birth_date=date(2007, 9, 2))),
        hoje=lambda: date(2026, 9, 2),
    )
    assert service.get_athlete_profile(USER_ID).age == 19


def test_idade_com_aniversario_de_29_de_fevereiro_em_ano_nao_bissexto():
    # Convencao adotada: em anos nao bissextos, o aniversario de quem nasceu em 29/fev
    # "acontece" em 1/mar (a comparacao (mes, dia) so passa a ser >= a partir de 1/mar,
    # ja que 2026 nao tem 29/fev). Antes dessa data o aniversario ainda nao ocorreu.
    service = ProfilesService(
        FakeRepository(um_record(birth_date=date(2008, 2, 29))),
        hoje=lambda: date(2026, 2, 28),
    )
    assert service.get_athlete_profile(USER_ID).age == 17

    service_apos = ProfilesService(
        FakeRepository(um_record(birth_date=date(2008, 2, 29))),
        hoje=lambda: date(2026, 3, 1),
    )
    assert service_apos.get_athlete_profile(USER_ID).age == 18


def test_sem_data_de_nascimento_a_idade_e_nula():
    service = ProfilesService(
        FakeRepository(um_record(birth_date=None)), hoje=lambda: date(2026, 9, 2)
    )
    assert service.get_athlete_profile(USER_ID).age is None


def test_perfil_inexistente_levanta_not_found():
    service = ProfilesService(FakeRepository(None), hoje=lambda: date(2026, 9, 2))
    with pytest.raises(NotFoundError):
        service.get_athlete_profile(USER_ID)


def test_inclui_a_contagem_de_clipes():
    service = ProfilesService(
        FakeRepository(um_record(), clips=42), hoje=lambda: date(2026, 9, 2)
    )
    assert service.get_athlete_profile(USER_ID).clips_count == 42


def test_atualizacao_parcial_so_repassa_os_campos_enviados():
    repo = FakeRepository(um_record())
    service = ProfilesService(repo, hoje=lambda: date(2026, 9, 2))
    service.update_athlete_profile(USER_ID, {"city": "Santos"})
    assert repo.ultima_atualizacao == {"city": "Santos"}


def test_atualizar_perfil_inexistente_levanta_not_found():
    service = ProfilesService(FakeRepository(None), hoje=lambda: date(2026, 9, 2))
    with pytest.raises(NotFoundError):
        service.update_athlete_profile(USER_ID, {"city": "Santos"})

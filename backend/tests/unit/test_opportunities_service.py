"""Regras puras de peneira: sem banco."""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.exceptions import ValidationError
from app.modules.opportunities.models import Opportunity, OpportunityMode
from app.modules.opportunities.service import (
    esta_aberta,
    motivo_inelegivel,
    validar_e_normalizar,
)
from app.modules.profiles.models import AthleteProfile, Position

AGORA = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
HOJE = AGORA.date()


def _opp(**over) -> Opportunity:
    dados = dict(
        title="Peneira",
        description="Avaliação",
        mode=OpportunityMode.PRESENCIAL,
        state="sp",
        city="Campinas",
        address="Rua A, 100",
        meeting_url=None,
        event_at=AGORA + timedelta(days=10),
        registration_deadline=AGORA + timedelta(days=5),
        min_age=None,
        max_age=None,
        positions=[],
        max_applications=None,
        cancelled_at=None,
    )
    dados.update(over)
    return Opportunity(**dados)


def _perfil(birth_date=date(2008, 5, 1), position=Position.ATACANTE) -> AthleteProfile:
    return AthleteProfile(birth_date=birth_date, position=position)


# --- elegibilidade -----------------------------------------------------------------

def test_sem_restricoes_qualquer_atleta_e_elegivel_mesmo_sem_perfil():
    assert motivo_inelegivel(_opp(), None, HOJE) is None


def test_idade_no_limite_exato_e_elegivel():
    # faz 18 anos exatamente hoje
    perfil = _perfil(birth_date=date(2008, 11, 11))
    assert motivo_inelegivel(_opp(min_age=18, max_age=18), perfil, HOJE) is None


def test_um_dia_antes_do_aniversario_ainda_tem_a_idade_anterior():
    perfil = _perfil(birth_date=date(2008, 11, 12))  # 17 anos
    assert motivo_inelegivel(_opp(min_age=18), perfil, HOJE) == "Idade mínima: 18 anos."


def test_acima_da_idade_maxima():
    perfil = _perfil(birth_date=date(2000, 1, 1))
    assert motivo_inelegivel(_opp(max_age=20), perfil, HOJE) == "Idade máxima: 20 anos."


def test_posicao_aceita_e_recusada():
    opp = _opp(positions=["GOLEIRO", "ZAGUEIRO"])
    assert motivo_inelegivel(opp, _perfil(position=Position.GOLEIRO), HOJE) is None
    assert (
        motivo_inelegivel(opp, _perfil(position=Position.ATACANTE), HOJE)
        == "Sua posição não está entre as aceitas nesta peneira."
    )


def test_perfil_incompleto_lista_o_que_falta():
    opp = _opp(min_age=15, positions=["MEIA"])
    perfil = _perfil(birth_date=None, position=None)
    assert motivo_inelegivel(opp, perfil, HOJE) == (
        "Complete seu perfil (data de nascimento e posição) para se inscrever nesta peneira."
    )


def test_sem_perfil_e_peneira_com_restricao_pede_para_completar():
    assert "data de nascimento" in motivo_inelegivel(_opp(max_age=17), None, HOJE)


# --- aberta ------------------------------------------------------------------------

def test_aberta_com_prazo_futuro_e_sem_limite():
    assert esta_aberta(_opp(), ocupadas=0, agora=AGORA)


def test_fechada_quando_cancelada():
    assert not esta_aberta(_opp(cancelled_at=AGORA), ocupadas=0, agora=AGORA)


def test_fechada_quando_prazo_venceu():
    opp = _opp(registration_deadline=AGORA - timedelta(seconds=1))
    assert not esta_aberta(opp, ocupadas=0, agora=AGORA)


def test_aberta_no_instante_exato_do_prazo():
    assert esta_aberta(_opp(registration_deadline=AGORA), ocupadas=0, agora=AGORA)


def test_fechada_quando_vagas_esgotadas():
    assert not esta_aberta(_opp(max_applications=2), ocupadas=2, agora=AGORA)
    assert esta_aberta(_opp(max_applications=2), ocupadas=1, agora=AGORA)


# --- validação ---------------------------------------------------------------------

def test_presencial_valido_zera_link_e_normaliza_uf():
    opp = _opp(meeting_url="https://x")
    validar_e_normalizar(opp)
    assert opp.meeting_url is None
    assert opp.state == "SP"


def test_presencial_sem_endereco_e_invalido():
    with pytest.raises(ValidationError, match="UF, cidade e endereço"):
        validar_e_normalizar(_opp(address=None))


def test_online_sem_link_e_invalido():
    with pytest.raises(ValidationError, match="link da reunião"):
        validar_e_normalizar(_opp(mode=OpportunityMode.ONLINE, meeting_url=None))


def test_online_valido_zera_local():
    opp = _opp(mode=OpportunityMode.ONLINE, meeting_url="https://meet.example.com/x")
    validar_e_normalizar(opp)
    assert (opp.state, opp.city, opp.address) == (None, None, None)


def test_prazo_depois_do_evento_e_invalido():
    opp = _opp(registration_deadline=AGORA + timedelta(days=11))
    with pytest.raises(ValidationError, match="prazo"):
        validar_e_normalizar(opp)


def test_idade_minima_maior_que_maxima_e_invalido():
    with pytest.raises(ValidationError, match="Idade mínima"):
        validar_e_normalizar(_opp(min_age=18, max_age=15))


def test_campo_obrigatorio_nulo_e_invalido():
    with pytest.raises(ValidationError, match="obrigatórios"):
        validar_e_normalizar(_opp(title=None))

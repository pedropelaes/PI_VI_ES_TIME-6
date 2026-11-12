"""Regras de negócio das peneiras. Funções puras: recebem dados, não sessão."""
from datetime import date, datetime
from typing import Optional

from app.core.exceptions import ValidationError
from app.modules.opportunities.models import Opportunity, OpportunityMode
from app.modules.profiles.models import AthleteProfile
from app.modules.profiles.service import calcular_idade


def motivo_inelegivel(
    opp: Opportunity, perfil: Optional[AthleteProfile], hoje: date
) -> Optional[str]:
    """None = elegível. Senão, o motivo em texto para mostrar ao atleta."""
    exige_idade = opp.min_age is not None or opp.max_age is not None
    exige_posicao = bool(opp.positions)

    faltando = []
    if exige_idade and (perfil is None or perfil.birth_date is None):
        faltando.append("data de nascimento")
    if exige_posicao and (perfil is None or perfil.position is None):
        faltando.append("posição")
    if faltando:
        return f"Complete seu perfil ({' e '.join(faltando)}) para se inscrever nesta peneira."

    if exige_idade:
        idade = calcular_idade(perfil.birth_date, hoje)
        if opp.min_age is not None and idade < opp.min_age:
            return f"Idade mínima: {opp.min_age} anos."
        if opp.max_age is not None and idade > opp.max_age:
            return f"Idade máxima: {opp.max_age} anos."
    if exige_posicao and perfil.position.value not in opp.positions:
        return "Sua posição não está entre as aceitas nesta peneira."
    return None


def esta_aberta(opp: Opportunity, ocupadas: int, agora: datetime) -> bool:
    """Aberta = não cancelada, prazo não vencido e com vaga (spec D5)."""
    if opp.cancelled_at is not None or opp.registration_deadline < agora:
        return False
    return opp.max_applications is None or ocupadas < opp.max_applications


def validar_e_normalizar(opp: Opportunity) -> None:
    """Zera os campos do modo que não vale e valida o resto. Levanta ValidationError."""
    if not (opp.title and opp.description and opp.mode and opp.event_at and opp.registration_deadline):
        raise ValidationError("Título, descrição, modalidade e datas são obrigatórios.")

    if opp.mode == OpportunityMode.PRESENCIAL:
        opp.meeting_url = None
        if not (opp.state and opp.city and opp.address):
            raise ValidationError("Peneira presencial precisa de UF, cidade e endereço.")
        opp.state = opp.state.upper()
    else:
        opp.state = opp.city = opp.address = None
        if not opp.meeting_url:
            raise ValidationError("Peneira online precisa do link da reunião.")

    if opp.registration_deadline > opp.event_at:
        raise ValidationError("O prazo de inscrição não pode ser depois do evento.")
    if opp.min_age is not None and opp.max_age is not None and opp.min_age > opp.max_age:
        raise ValidationError("Idade mínima não pode ser maior que a máxima.")

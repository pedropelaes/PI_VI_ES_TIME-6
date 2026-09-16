"""
Regras de negocio do chat interno: quem pode ver o que, como uma conversa nasce e como
mensagens viram "lidas". O router so traduz HTTP <-> estes metodos.

Devolve dataclasses congeladas (`Record`), nunca objetos ORM -- mesma convencao do
modulo `profiles` (ver `profiles/repository.py`): mantém o service testavel sem
precisar de uma Session de verdade e evita vazar a Session para fora da transacao.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Session, func, or_, select

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.modules.identity.models import User, UserRole
from app.modules.messaging.models import Conversation, Message
from app.modules.profiles.models import AthleteProfile, ClubProfile, ScoutProfile


def _agora() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ParticipantRecord:
    """O outro lado de uma conversa, com o suficiente para a lista e o cabecalho do chat."""

    id: uuid.UUID
    first_name: str
    last_name: str
    role: UserRole
    avatar_path: Optional[str]


@dataclass(frozen=True)
class MessageRecord:
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    body: str
    created_at: datetime
    read_at: Optional[datetime]


@dataclass(frozen=True)
class MessagePage:
    """Uma pagina de `list_messages`, da mais antiga para a mais nova."""

    messages: List[MessageRecord]
    has_more: bool


@dataclass(frozen=True)
class ConversationRecord:
    """Uma linha da lista de conversas, ja do ponto de vista de quem esta autenticado."""

    id: uuid.UUID
    participant: ParticipantRecord
    last_message: Optional[MessageRecord]
    unread_count: int
    last_message_at: datetime


def _to_message_record(message: Message) -> MessageRecord:
    return MessageRecord(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        body=message.body,
        created_at=message.created_at,
        read_at=message.read_at,
    )


class MessagingService:
    def __init__(self, session: Session):
        self.session = session

    # -- participantes -----------------------------------------------------

    def _avatar_path_for(self, user: User) -> Optional[str]:
        """
        O avatar mora na tabela de perfil do papel, nao em `users` (mesmo desenho do
        modulo `profiles`). Um usuario sem perfil ainda criado (inconsistencia de
        cadastro) simplesmente nao tem avatar aqui -- nao e erro desta camada.
        """
        modelo_por_papel = {
            UserRole.ATHLETE: AthleteProfile,
            UserRole.SCOUT: ScoutProfile,
            UserRole.CLUB: ClubProfile,
        }
        modelo = modelo_por_papel.get(user.role)
        if modelo is None:  # pragma: no cover - so alcancavel adicionando um papel novo
            return None

        perfil = self.session.get(modelo, user.id)
        return perfil.avatar_path if perfil else None

    def _to_participant_record(self, user: User) -> ParticipantRecord:
        return ParticipantRecord(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            avatar_path=self._avatar_path_for(user),
        )

    # -- conversas -----------------------------------------------------------

    @staticmethod
    def _canonical_pair(user_id: uuid.UUID, other_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
        """
        Ordena o par pela representacao textual do UUID: e so o que faz duas buscas
        pela mesma dupla (A,B) e (B,A) caírem na mesma linha em `conversations`,
        qualquer que seja quem inicia. A ordem em si nao tem significado.
        """
        return (user_id, other_id) if str(user_id) < str(other_id) else (other_id, user_id)

    def get_or_create_conversation(
        self, user_id: uuid.UUID, other_user_id: uuid.UUID
    ) -> ConversationRecord:
        if user_id == other_user_id:
            raise ValidationError("Não é possível iniciar uma conversa consigo mesmo.")

        other = self.session.get(User, other_user_id)
        if other is None:
            raise NotFoundError("Usuário não encontrado.")

        a, b = self._canonical_pair(user_id, other_user_id)
        conversa = self.session.exec(
            select(Conversation).where(
                Conversation.participant_a_id == a, Conversation.participant_b_id == b
            )
        ).first()

        if conversa is None:
            conversa = Conversation(participant_a_id=a, participant_b_id=b)
            self.session.add(conversa)
            self.session.flush()
            self.session.refresh(conversa)

        return self._to_conversation_record(conversa, user_id)

    def _require_participant(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation:
        conversa = self.session.get(Conversation, conversation_id)
        if conversa is None:
            raise NotFoundError("Conversa não encontrada.")

        if user_id not in (conversa.participant_a_id, conversa.participant_b_id):
            # Mesma logica de "404 disfarcado de 403" que o resto do app nao usa aqui:
            # ao contrario de um perfil, a existencia de uma conversa alheia nao e
            # informacao sensivel por si so, entao 403 e honesto.
            raise ForbiddenError("Você não participa desta conversa.")

        return conversa

    def _other_participant_id(self, conversa: Conversation, user_id: uuid.UUID) -> uuid.UUID:
        return (
            conversa.participant_b_id
            if conversa.participant_a_id == user_id
            else conversa.participant_a_id
        )

    def other_participant_id(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> uuid.UUID:
        """Para quem, alem do proprio `user_id`, um evento desta conversa deve ir (WS)."""
        conversa = self._require_participant(conversation_id, user_id)
        return self._other_participant_id(conversa, user_id)

    def _to_conversation_record(
        self, conversa: Conversation, user_id: uuid.UUID
    ) -> ConversationRecord:
        other_id = self._other_participant_id(conversa, user_id)
        other_user = self.session.get(User, other_id)
        assert other_user is not None  # integridade referencial garante isso

        ultima = self.session.exec(
            select(Message)
            .where(Message.conversation_id == conversa.id)
            .order_by(Message.created_at.desc())
        ).first()

        nao_lidas = self.session.exec(
            select(func.count(Message.id)).where(
                Message.conversation_id == conversa.id,
                Message.sender_id != user_id,
                Message.read_at.is_(None),
            )
        ).one()

        return ConversationRecord(
            id=conversa.id,
            participant=self._to_participant_record(other_user),
            last_message=_to_message_record(ultima) if ultima else None,
            unread_count=int(nao_lidas),
            last_message_at=conversa.last_message_at,
        )

    def list_conversations(self, user_id: uuid.UUID) -> List[ConversationRecord]:
        conversas = self.session.exec(
            select(Conversation)
            .where(
                or_(
                    Conversation.participant_a_id == user_id,
                    Conversation.participant_b_id == user_id,
                )
            )
            .order_by(Conversation.last_message_at.desc())
        ).all()

        return [self._to_conversation_record(c, user_id) for c in conversas]

    def unread_total(self, user_id: uuid.UUID) -> int:
        """Soma de nao lidas em todas as conversas, para o badge do header."""
        total = self.session.exec(
            select(func.count(Message.id))
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                or_(
                    Conversation.participant_a_id == user_id,
                    Conversation.participant_b_id == user_id,
                ),
                Message.sender_id != user_id,
                Message.read_at.is_(None),
            )
        ).one()
        return int(total)

    # -- mensagens -------------------------------------------------------------

    def list_messages(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 50,
        before: Optional[datetime] = None,
    ) -> MessagePage:
        """
        As `limit` mensagens mais recentes antes de `before` (ou de agora, se ausente),
        devolvidas da mais antiga para a mais nova -- ordem pronta para renderizar sem
        o cliente precisar inverter a lista.
        """
        self._require_participant(conversation_id, user_id)

        query = select(Message).where(Message.conversation_id == conversation_id)
        if before is not None:
            query = query.where(Message.created_at < before)

        # Busca uma a mais do que o pedido só para saber se há próxima página, sem
        # precisar de um segundo COUNT(*) -- ela é descartada antes de devolver.
        pagina = self.session.exec(
            query.order_by(Message.created_at.desc()).limit(limit + 1)
        ).all()

        has_more = len(pagina) > limit
        mensagens = pagina[:limit]

        return MessagePage(
            messages=[_to_message_record(m) for m in reversed(mensagens)],
            has_more=has_more,
        )

    def send_message(
        self, conversation_id: uuid.UUID, sender_id: uuid.UUID, body: str
    ) -> MessageRecord:
        conversa = self._require_participant(conversation_id, sender_id)

        texto = body.strip()
        if not texto:
            raise ValidationError("A mensagem não pode ser vazia.")

        mensagem = Message(conversation_id=conversa.id, sender_id=sender_id, body=texto)
        self.session.add(mensagem)

        conversa.last_message_at = mensagem.created_at
        self.session.add(conversa)

        self.session.flush()
        self.session.refresh(mensagem)
        return _to_message_record(mensagem)

    def mark_conversation_read(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        conversa = self._require_participant(conversation_id, user_id)

        nao_lidas = self.session.exec(
            select(Message).where(
                Message.conversation_id == conversa.id,
                Message.sender_id != user_id,
                Message.read_at.is_(None),
            )
        ).all()

        agora = _agora()
        for mensagem in nao_lidas:
            mensagem.read_at = agora
            self.session.add(mensagem)

        self.session.flush()

"""DTOs de entrada e saida do modulo de mensagens."""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.modules.identity.models import UserRole
from app.modules.messaging.service import ConversationRecord, MessagePage, MessageRecord


class ParticipantOut(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    role: UserRole
    # `avatar_path` na origem; para o cliente e uma URL, mesma convencao de
    # `avatar_url` em profiles/schemas.py.
    avatar_url: Optional[str]


class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    body: str
    created_at: datetime
    read_at: Optional[datetime]

    @classmethod
    def from_record(cls, record: MessageRecord) -> "MessageOut":
        return cls(
            id=record.id,
            conversation_id=record.conversation_id,
            sender_id=record.sender_id,
            body=record.body,
            created_at=record.created_at,
            read_at=record.read_at,
        )


class ConversationOut(BaseModel):
    id: uuid.UUID
    participant: ParticipantOut
    last_message: Optional[MessageOut]
    unread_count: int
    last_message_at: datetime

    @classmethod
    def from_record(cls, record: ConversationRecord) -> "ConversationOut":
        return cls(
            id=record.id,
            participant=ParticipantOut(
                id=record.participant.id,
                first_name=record.participant.first_name,
                last_name=record.participant.last_name,
                role=record.participant.role,
                avatar_url=record.participant.avatar_path,
            ),
            last_message=MessageOut.from_record(record.last_message)
            if record.last_message
            else None,
            unread_count=record.unread_count,
            last_message_at=record.last_message_at,
        )


class ConversationCreate(BaseModel):
    """Quem o autenticado quer conversar. Se ja existir conversa com essa pessoa, ela e
    reaproveitada em vez de duplicada -- ver `MessagingService.get_or_create_conversation`.
    """

    recipient_id: uuid.UUID


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class UnreadCountOut(BaseModel):
    count: int


class MessageListOut(BaseModel):
    """Envelope da lista de mensagens: `has_more` diz se ha mais paginas para tras."""

    messages: List[MessageOut]
    has_more: bool

    @classmethod
    def from_page(cls, page: MessagePage) -> "MessageListOut":
        return cls(
            messages=[MessageOut.from_record(m) for m in page.messages],
            has_more=page.has_more,
        )

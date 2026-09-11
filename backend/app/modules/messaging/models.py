import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, SQLModel


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(SQLModel, table=True):
    """
    Conversa 1:1 entre dois usuarios, qualquer que seja o papel de cada um.

    O par de participantes e canonicalizado na criacao (`participant_a_id` <
    `participant_b_id`, comparando os UUID como texto) para que a mesma dupla nunca
    abra duas conversas -- ver `MessagingService.get_or_create_conversation`. A
    ordem nao tem outro significado; nao ha "quem comecou a conversa".
    """

    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint(
            "participant_a_id", "participant_b_id", name="uq_conversations_participants"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    participant_a_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    participant_b_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=_agora)
    # Denormalizado a partir da ultima Message para ordenar a lista de conversas sem
    # precisar de um LEFT JOIN + agregacao a cada `GET /messages/conversations`.
    last_message_at: datetime = Field(default_factory=_agora, index=True)


class Message(SQLModel, table=True):
    """Mensagem de texto de um participante para a conversa."""

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: uuid.UUID = Field(foreign_key="conversations.id", index=True)
    sender_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    body: str
    created_at: datetime = Field(default_factory=_agora, index=True)
    # None ate o destinatario abrir a conversa; nunca setado para o proprio remetente.
    read_at: Optional[datetime] = Field(default=None)

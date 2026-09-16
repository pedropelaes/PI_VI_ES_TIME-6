"""
HTTP do chat interno: rota, validacao e serializacao. Sem regra de negocio -- tudo isso
vive em `MessagingService`. Erros de dominio sobem como excecao e sao traduzidos pelo
handler unico de `main.py`, igual ao restante do app.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.security import decode_access_token
from app.modules.identity.models import User
from app.modules.messaging.connection_manager import manager
from app.modules.messaging.schemas import (
    ConversationCreate,
    ConversationOut,
    MessageCreate,
    MessageListOut,
    MessageOut,
    UnreadCountOut,
)
from app.modules.messaging.service import MessagingService

router = APIRouter(prefix="/messages", tags=["messages"])


def get_service(session: Session = Depends(get_session)) -> MessagingService:
    return MessagingService(session)


@router.get("/conversations", response_model=List[ConversationOut])
def list_conversations(
    service: MessagingService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Conversas do autenticado, mais recente primeiro."""
    return [
        ConversationOut.from_record(record)
        for record in service.list_conversations(current_user.id)
    ]


@router.post("/conversations", response_model=ConversationOut, status_code=201)
def create_conversation(
    payload: ConversationCreate,
    service: MessagingService = Depends(get_service),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Abre (ou reaproveita) a conversa com `recipient_id`.

    E o ponto de entrada de "Enviar Mensagem" num perfil: idempotente, entao clicar de
    novo num perfil com quem ja se conversa so devolve a conversa existente em vez de
    criar uma nova vazia ao lado.
    """
    record = service.get_or_create_conversation(current_user.id, payload.recipient_id)
    session.commit()
    return ConversationOut.from_record(record)


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListOut)
def list_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[datetime] = Query(
        None, description="Devolve mensagens estritamente anteriores a este instante."
    ),
    service: MessagingService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """
    Mensagens da conversa, da mais antiga para a mais nova. `before` pagina para tras
    (scroll para mensagens mais antigas); sem ele, traz a janela mais recente.
    """
    page = service.list_messages(conversation_id, current_user.id, limit=limit, before=before)
    return MessageListOut.from_page(page)


@router.post(
    "/conversations/{conversation_id}/messages", response_model=MessageOut, status_code=201
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    service: MessagingService = Depends(get_service),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    record = service.send_message(conversation_id, current_user.id, payload.body)
    session.commit()
    resposta = MessageOut.from_record(record)

    # O POST continua sendo quem persiste (fonte unica da verdade); o push por WS e so
    # para quem esta com a tela aberta agora nao precisar esperar o proximo poll.
    # Manda tambem para o proprio remetente: outra aba dele deve refletir o envio.
    destinatario_id = service.other_participant_id(conversation_id, current_user.id)
    evento = {"type": "new_message", "message": resposta.model_dump(mode="json")}
    await manager.send_to_user(destinatario_id, evento)
    await manager.send_to_user(current_user.id, evento)

    return resposta


@router.post("/conversations/{conversation_id}/read", status_code=204)
async def mark_conversation_read(
    conversation_id: uuid.UUID,
    service: MessagingService = Depends(get_service),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Marca como lidas todas as mensagens que o autenticado ainda nao tinha lido."""
    destinatario_id = service.other_participant_id(conversation_id, current_user.id)
    service.mark_conversation_read(conversation_id, current_user.id)
    session.commit()

    # Avisa quem mandou as mensagens: e o que faz os dois riscos ficarem azuis na hora
    # na tela de quem enviou, sem esperar ela reabrir a conversa.
    await manager.send_to_user(
        destinatario_id,
        {"type": "conversation_read", "conversation_id": str(conversation_id)},
    )
    return None


@router.get("/unread-count", response_model=UnreadCountOut)
def get_unread_count(
    service: MessagingService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Total de nao lidas em todas as conversas, para o badge do header."""
    return UnreadCountOut(count=service.unread_total(current_user.id))


@router.websocket("/ws")
async def messaging_websocket(websocket: WebSocket, session: Session = Depends(get_session)):
    """
    Canal de entrega em tempo real: `send_message` e `mark_conversation_read` acima
    continuam sendo quem persiste e valida (fonte unica da verdade); este socket so
    empurra o evento pra quem estiver com a Inbox aberta agora.

    A autenticacao vem em `?token=`, nao no header Authorization: a API de WebSocket do
    navegador nao permite header customizado no handshake, entao o mesmo JWT de sempre
    viaja na query string.
    """
    token = websocket.query_params.get("token")
    user_id_str = decode_access_token(token) if token else None

    if not user_id_str:
        await websocket.close(code=4401)
        return

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        await websocket.close(code=4401)
        return

    if session.get(User, user_id) is None:
        await websocket.close(code=4401)
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            # Nada e esperado do cliente por este socket -- o envio de mensagem
            # continua sendo o POST REST. O receive so existe para dar a este loop
            # algo para esperar ate o navegador fechar a conexao.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, websocket)

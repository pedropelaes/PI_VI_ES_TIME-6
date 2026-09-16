import { httpGet, httpPost } from '../../shared/lib/httpClient';
import type { ConversationDTO, MessageDTO, MessageListDTO } from './types';

export function getConversations(): Promise<ConversationDTO[]> {
  return httpGet<ConversationDTO[]>('/messages/conversations');
}

/**
 * Idempotente do lado do servidor: chamar de novo para o mesmo destinatario
 * devolve a conversa ja existente em vez de criar uma nova vazia ao lado.
 */
export function startConversation(recipientId: string): Promise<ConversationDTO> {
  return httpPost<ConversationDTO>('/messages/conversations', { recipient_id: recipientId });
}

export function getMessages(
  conversationId: string,
  before?: string
): Promise<MessageListDTO> {
  const query = before ? `?before=${encodeURIComponent(before)}` : '';
  return httpGet<MessageListDTO>(`/messages/conversations/${conversationId}/messages${query}`);
}

export function sendMessage(conversationId: string, body: string): Promise<MessageDTO> {
  return httpPost<MessageDTO>(`/messages/conversations/${conversationId}/messages`, { body });
}

export function markConversationRead(conversationId: string): Promise<void> {
  return httpPost<void>(`/messages/conversations/${conversationId}/read`);
}

export function getUnreadCount(): Promise<{ count: number }> {
  return httpGet<{ count: number }>('/messages/unread-count');
}

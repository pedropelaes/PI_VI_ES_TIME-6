import type { UserRole } from '../../shared/lib/userRole';

/** Resposta crua da API para o outro participante de uma conversa. */
export interface ParticipantDTO {
  id: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  avatar_url: string | null;
}

/** Resposta crua de uma mensagem. */
export interface MessageDTO {
  id: string;
  conversation_id: string;
  sender_id: string;
  body: string;
  created_at: string;
  read_at: string | null;
}

/** Resposta crua de GET /messages/conversations, um item da lista. */
export interface ConversationDTO {
  id: string;
  participant: ParticipantDTO;
  last_message: MessageDTO | null;
  unread_count: number;
  last_message_at: string;
}

/** Envelope de GET /messages/conversations/{id}/messages. */
export interface MessageListDTO {
  messages: MessageDTO[];
  has_more: boolean;
}

/** O que a lista de conversas consome: tudo ja formatado, sem logica no JSX. */
export interface ConversationView {
  id: string;
  participantId: string;
  fullName: string;
  initial: string;
  roleLabel: string;
  avatarUrl: string | null;
  lastMessagePreview: string;
  timeLabel: string;
  unreadCount: number;
  lastMessageAt: string;
}

/** O que a coluna de mensagens consome. */
export interface MessageView {
  id: string;
  body: string;
  timeLabel: string;
  mine: boolean;
  read: boolean;
}

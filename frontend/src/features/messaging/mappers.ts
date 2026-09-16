import { resolveAvatarUrl } from '../profiles/mappers';
import { USER_ROLE_LABELS } from '../../shared/lib/userRole';
import type { ConversationDTO, ConversationView, MessageDTO, MessageView } from './types';

const DIAS_DA_SEMANA = [
  'Domingo',
  'Segunda',
  'Terça',
  'Quarta',
  'Quinta',
  'Sexta',
  'Sábado',
];

function horaCurta(data: Date): string {
  return data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function mesmoDia(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

/**
 * Rotulo relativo do horario da ultima mensagem, igual ao mock original: hoje mostra
 * a hora, ontem mostra "Ontem", ate 6 dias atras mostra o dia da semana, e mais velho
 * que isso mostra a data curta.
 */
export function formatConversationTime(isoDate: string): string {
  const data = new Date(isoDate);
  const agora = new Date();

  if (mesmoDia(data, agora)) {
    return horaCurta(data);
  }

  const ontem = new Date(agora);
  ontem.setDate(ontem.getDate() - 1);
  if (mesmoDia(data, ontem)) {
    return 'Ontem';
  }

  const diasAtras = Math.floor((agora.getTime() - data.getTime()) / (1000 * 60 * 60 * 24));
  if (diasAtras < 7) {
    return DIAS_DA_SEMANA[data.getDay()];
  }

  return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

export function toConversationView(dto: ConversationDTO): ConversationView {
  const fullName = `${dto.participant.first_name} ${dto.participant.last_name}`.trim();

  return {
    id: dto.id,
    participantId: dto.participant.id,
    fullName,
    initial: dto.participant.first_name.charAt(0).toUpperCase(),
    roleLabel: USER_ROLE_LABELS[dto.participant.role],
    avatarUrl: resolveAvatarUrl(dto.participant.avatar_url),
    lastMessagePreview: dto.last_message?.body ?? 'Nenhuma mensagem ainda.',
    timeLabel: formatConversationTime(dto.last_message_at),
    unreadCount: dto.unread_count,
    lastMessageAt: dto.last_message_at,
  };
}

export function toMessageView(dto: MessageDTO, myUserId: string): MessageView {
  return {
    id: dto.id,
    body: dto.body,
    timeLabel: horaCurta(new Date(dto.created_at)),
    mine: dto.sender_id === myUserId,
    read: dto.read_at !== null,
  };
}

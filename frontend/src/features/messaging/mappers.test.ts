import { describe, expect, it } from 'vitest';
import { formatConversationTime, toConversationView, toMessageView } from './mappers';
import type { ConversationDTO, MessageDTO } from './types';

const PARTICIPANT_DTO: ConversationDTO['participant'] = {
  id: 'scout-1',
  first_name: 'Ana',
  last_name: 'Souza',
  role: 'SCOUT',
  avatar_url: null,
};

function conversaDTO(overrides: Partial<ConversationDTO> = {}): ConversationDTO {
  return {
    id: 'conv-1',
    participant: PARTICIPANT_DTO,
    last_message: null,
    unread_count: 0,
    last_message_at: new Date().toISOString(),
    ...overrides,
  };
}

describe('formatConversationTime', () => {
  it('mostra a hora quando a mensagem e de hoje', () => {
    const agora = new Date();
    expect(formatConversationTime(agora.toISOString())).toMatch(/^\d{2}:\d{2}$/);
  });

  it('mostra "Ontem" quando a mensagem e do dia anterior', () => {
    const ontem = new Date();
    ontem.setDate(ontem.getDate() - 1);
    expect(formatConversationTime(ontem.toISOString())).toBe('Ontem');
  });

  it('mostra o dia da semana ate 6 dias atras', () => {
    const tresDiasAtras = new Date();
    tresDiasAtras.setDate(tresDiasAtras.getDate() - 3);
    const rotulo = formatConversationTime(tresDiasAtras.toISOString());
    expect(['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']).toContain(
      rotulo
    );
  });

  it('mostra data curta para mensagens mais antigas que uma semana', () => {
    const duasSemanasAtras = new Date();
    duasSemanasAtras.setDate(duasSemanasAtras.getDate() - 15);
    expect(formatConversationTime(duasSemanasAtras.toISOString())).toMatch(/^\d{2}\/\d{2}$/);
  });
});

describe('toConversationView', () => {
  it('junta nome e sobrenome, e usa a inicial do primeiro nome', () => {
    const view = toConversationView(conversaDTO());
    expect(view.fullName).toBe('Ana Souza');
    expect(view.initial).toBe('A');
  });

  it('traduz o papel para portugues', () => {
    expect(toConversationView(conversaDTO()).roleLabel).toBe('Scout');
  });

  it('usa o texto padrao quando nao ha mensagem ainda', () => {
    expect(toConversationView(conversaDTO()).lastMessagePreview).toBe(
      'Nenhuma mensagem ainda.'
    );
  });

  it('usa o corpo da ultima mensagem quando existe', () => {
    const dto = conversaDTO({
      last_message: {
        id: 'm1',
        conversation_id: 'conv-1',
        sender_id: 'scout-1',
        body: 'Oi, tudo bem?',
        created_at: new Date().toISOString(),
        read_at: null,
      },
    });
    expect(toConversationView(dto).lastMessagePreview).toBe('Oi, tudo bem?');
  });

  it('preserva o unread_count e o id da conversa', () => {
    const dto = conversaDTO({ unread_count: 3 });
    const view = toConversationView(dto);
    expect(view.unreadCount).toBe(3);
    expect(view.id).toBe('conv-1');
    expect(view.participantId).toBe('scout-1');
  });
});

describe('toMessageView', () => {
  const MESSAGE_DTO: MessageDTO = {
    id: 'm1',
    conversation_id: 'conv-1',
    sender_id: 'scout-1',
    body: 'Oi!',
    created_at: new Date().toISOString(),
    read_at: null,
  };

  it('marca como minha quando o remetente e o usuario logado', () => {
    expect(toMessageView(MESSAGE_DTO, 'scout-1').mine).toBe(true);
    expect(toMessageView(MESSAGE_DTO, 'outro-id').mine).toBe(false);
  });

  it('reflete se a mensagem ja foi lida', () => {
    expect(toMessageView(MESSAGE_DTO, 'scout-1').read).toBe(false);
    expect(
      toMessageView({ ...MESSAGE_DTO, read_at: new Date().toISOString() }, 'scout-1').read
    ).toBe(true);
  });
});

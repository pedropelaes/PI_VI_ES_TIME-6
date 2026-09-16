import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useMessagingSocket } from './useMessagingSocket';
import { CONVERSATIONS_QUERY_KEY } from './useConversations';
import { messagesQueryKey } from './useConversationMessages';
import { UNREAD_COUNT_QUERY_KEY } from './useUnreadCount';
import type { MessageListDTO } from '../types';

/** Dublê de WebSocket: captura a URL e deixa o teste disparar onmessage/onclose. */
class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  url: string;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  close() {
    this.closed = true;
  }

  emit(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }
}

function criarClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function wrapperCom(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  vi.stubGlobal('WebSocket', FakeWebSocket);
  localStorage.setItem('access_token', 'token-de-teste');
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  localStorage.clear();
});

describe('useMessagingSocket', () => {
  it('nao abre conexao sem usuario logado', () => {
    renderHook(() => useMessagingSocket(undefined), { wrapper: wrapperCom(criarClient()) });

    expect(FakeWebSocket.instances).toHaveLength(0);
  });

  it('abre a conexao com o token na query string', () => {
    renderHook(() => useMessagingSocket('user-1'), { wrapper: wrapperCom(criarClient()) });

    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(FakeWebSocket.instances[0].url).toContain('/messages/ws?token=token-de-teste');
  });

  it('fecha o socket ao desmontar', () => {
    const { unmount } = renderHook(() => useMessagingSocket('user-1'), {
      wrapper: wrapperCom(criarClient()),
    });

    unmount();

    expect(FakeWebSocket.instances[0].closed).toBe(true);
  });

  it('acrescenta a mensagem nova ao cache da conversa e invalida lista e contador', () => {
    const client = criarClient();
    const chaveConversa = messagesQueryKey('conv-1');
    client.setQueryData<MessageListDTO>(chaveConversa, { messages: [], has_more: false });

    const invalidateSpy = vi.spyOn(client, 'invalidateQueries');

    renderHook(() => useMessagingSocket('user-1'), { wrapper: wrapperCom(client) });

    FakeWebSocket.instances[0].emit({
      type: 'new_message',
      message: {
        id: 'm1',
        conversation_id: 'conv-1',
        sender_id: 'outro',
        body: 'oi',
        created_at: '2026-01-01T10:00:00Z',
        read_at: null,
      },
    });

    expect(client.getQueryData<MessageListDTO>(chaveConversa)?.messages).toHaveLength(1);
    expect(
      invalidateSpy.mock.calls.some((c) => c[0]?.queryKey === CONVERSATIONS_QUERY_KEY)
    ).toBe(true);
    expect(
      invalidateSpy.mock.calls.some((c) => c[0]?.queryKey === UNREAD_COUNT_QUERY_KEY)
    ).toBe(true);
  });

  it('nao duplica mensagem que ja estava no cache', () => {
    const client = criarClient();
    const chaveConversa = messagesQueryKey('conv-1');
    const mensagem = {
      id: 'm1',
      conversation_id: 'conv-1',
      sender_id: 'outro',
      body: 'oi',
      created_at: '2026-01-01T10:00:00Z',
      read_at: null,
    };
    client.setQueryData<MessageListDTO>(chaveConversa, { messages: [mensagem], has_more: false });

    renderHook(() => useMessagingSocket('user-1'), { wrapper: wrapperCom(client) });
    FakeWebSocket.instances[0].emit({ type: 'new_message', message: mensagem });

    expect(client.getQueryData<MessageListDTO>(chaveConversa)?.messages).toHaveLength(1);
  });

  it('ignora mensagem nova de conversa sem cache (ninguem olhando ela agora)', () => {
    const client = criarClient();

    renderHook(() => useMessagingSocket('user-1'), { wrapper: wrapperCom(client) });

    expect(() =>
      FakeWebSocket.instances[0].emit({
        type: 'new_message',
        message: {
          id: 'm1',
          conversation_id: 'conv-sem-cache',
          sender_id: 'outro',
          body: 'oi',
          created_at: '2026-01-01T10:00:00Z',
          read_at: null,
        },
      })
    ).not.toThrow();
  });

  it('marca como lidas as proprias mensagens da conversa ao receber conversation_read', () => {
    const client = criarClient();
    const chaveConversa = messagesQueryKey('conv-1');
    client.setQueryData<MessageListDTO>(chaveConversa, {
      messages: [
        {
          id: 'm1',
          conversation_id: 'conv-1',
          sender_id: 'user-1',
          body: 'minha msg',
          created_at: '2026-01-01T10:00:00Z',
          read_at: null,
        },
        {
          id: 'm2',
          conversation_id: 'conv-1',
          sender_id: 'outro',
          body: 'msg dele',
          created_at: '2026-01-01T10:01:00Z',
          read_at: null,
        },
      ],
      has_more: false,
    });

    renderHook(() => useMessagingSocket('user-1'), { wrapper: wrapperCom(client) });
    FakeWebSocket.instances[0].emit({ type: 'conversation_read', conversation_id: 'conv-1' });

    const mensagens = client.getQueryData<MessageListDTO>(chaveConversa)?.messages ?? [];
    expect(mensagens.find((m) => m.id === 'm1')?.read_at).not.toBeNull();
    // A mensagem do outro participante nao e "lida por mim": read_at dela e sobre
    // quando EU li ela, nao quando ele leu a minha.
    expect(mensagens.find((m) => m.id === 'm2')?.read_at).toBeNull();
  });

  it('reconecta apos o socket fechar', () => {
    vi.useFakeTimers();
    const client = criarClient();

    renderHook(() => useMessagingSocket('user-1'), { wrapper: wrapperCom(client) });
    expect(FakeWebSocket.instances).toHaveLength(1);

    FakeWebSocket.instances[0].onclose?.();
    vi.advanceTimersByTime(3_000);

    expect(FakeWebSocket.instances).toHaveLength(2);
  });
});

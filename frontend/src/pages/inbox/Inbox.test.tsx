import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Inbox from './Inbox';

const EU = {
  id: 'atleta-1',
  email: 'jeh@teste.com',
  first_name: 'Jeh',
  last_name: 'Rodrigues',
  role: 'ATHLETE',
  max_clips_allowed: 20,
};

const SCOUT = {
  id: 'scout-1',
  first_name: 'Ana',
  last_name: 'Souza',
  role: 'SCOUT',
  avatar_url: null,
};

function conversa(overrides: Record<string, unknown> = {}) {
  return {
    id: 'conv-1',
    participant: SCOUT,
    last_message: { id: 'm0', conversation_id: 'conv-1', sender_id: 'scout-1', body: 'Oi!', created_at: new Date().toISOString(), read_at: null },
    unread_count: 1,
    last_message_at: new Date().toISOString(),
    ...overrides,
  };
}

function mensagem(overrides: Record<string, unknown> = {}) {
  return {
    id: 'm1',
    conversation_id: 'conv-1',
    sender_id: 'scout-1',
    body: 'Oi, tudo bem?',
    created_at: new Date().toISOString(),
    read_at: null,
    ...overrides,
  };
}

interface Call {
  url: string;
  method: string;
  body: unknown;
}

let calls: Call[];

/**
 * Roteia o fetch por metodo + caminho, igual ao mock de EditProfile.test.tsx. A lista
 * de conversas e mutavel: iniciar uma conversa nova (POST) faz o GET seguinte devolve-la,
 * do jeito que a API real se comportaria.
 */
function mockApi(handlers: {
  conversations?: unknown[];
  messages?: unknown[];
  onSend?: () => unknown;
  onStart?: () => { id: string; participant: unknown };
}) {
  const listaDeConversas = [...(handlers.conversations ?? [])] as Array<{ id: string }>;

  return vi
    .spyOn(globalThis, 'fetch')
    .mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';
      calls.push({ url, method, body: init?.body });

      if (method === 'GET' && /\/messages\/conversations\/[^/]+\/messages/.test(url)) {
        return new Response(
          JSON.stringify({ messages: handlers.messages ?? [], has_more: false }),
          { status: 200 }
        );
      }
      if (method === 'POST' && /\/messages\/conversations\/[^/]+\/messages$/.test(url)) {
        return new Response(
          JSON.stringify(handlers.onSend ? handlers.onSend() : mensagem()),
          { status: 201 }
        );
      }
      if (method === 'POST' && /\/messages\/conversations\/[^/]+\/read$/.test(url)) {
        return new Response(null, { status: 204 });
      }
      if (method === 'POST' && url.endsWith('/messages/conversations')) {
        const nova = handlers.onStart ? handlers.onStart() : conversa();
        if (!listaDeConversas.some((c) => c.id === nova.id)) {
          listaDeConversas.unshift(nova as { id: string });
        }
        return new Response(JSON.stringify(nova), { status: 201 });
      }
      if (method === 'GET' && url.endsWith('/messages/conversations')) {
        return new Response(JSON.stringify(listaDeConversas), { status: 200 });
      }

      return new Response(JSON.stringify({}), { status: 200 });
    });
}

function renderInbox(initialEntry = '/messages') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Inbox />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  calls = [];
  localStorage.setItem('user', JSON.stringify(EU));
  localStorage.setItem('access_token', 'token');
});

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe('Inbox — lista de conversas', () => {
  it('mostra estado vazio quando nao ha conversas', async () => {
    mockApi({ conversations: [] });

    renderInbox();

    expect(await screen.findByText('Você ainda não tem conversas.')).toBeInTheDocument();
  });

  it('lista as conversas e abre a primeira automaticamente', async () => {
    mockApi({ conversations: [conversa()], messages: [mensagem()] });

    renderInbox();

    expect(await screen.findByText('Ana Souza')).toBeInTheDocument();
    expect(await screen.findByText('Oi, tudo bem?')).toBeInTheDocument();
  });

  it('filtra a lista pelo nome digitado na busca', async () => {
    mockApi({
      conversations: [
        conversa(),
        conversa({
          id: 'conv-2',
          participant: { ...SCOUT, id: 'clube-1', first_name: 'Ponte', last_name: 'Negra', role: 'CLUB' },
          last_message: null,
          unread_count: 0,
        }),
      ],
      messages: [],
    });

    renderInbox();
    await screen.findByText('Ana Souza');
    expect(screen.getByText('Ponte Negra')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Buscar conversas...'), {
      target: { value: 'ponte' },
    });

    // "Ana Souza" some da lista filtrada, mas continua no cabecalho do chat aberto
    // (a conversa ativa nao muda so porque a busca escondeu o item na barra lateral).
    expect(screen.getAllByText('Ana Souza')).toHaveLength(1);
    expect(screen.getByText('Ponte Negra')).toBeInTheDocument();
  });

  it('marca a conversa como lida ao abrir', async () => {
    mockApi({ conversations: [conversa()], messages: [mensagem()] });

    renderInbox();
    await screen.findByText('Oi, tudo bem?');

    await waitFor(() =>
      expect(calls.some((c) => c.method === 'POST' && c.url.endsWith('/conv-1/read'))).toBe(
        true
      )
    );
  });
});

describe('Inbox — envio de mensagens', () => {
  it('envia mensagem digitada e limpa o campo', async () => {
    mockApi({ conversations: [conversa()], messages: [mensagem()] });

    renderInbox();
    await screen.findByText('Oi, tudo bem?');

    const campo = screen.getByPlaceholderText('Escreva sua mensagem...');
    fireEvent.change(campo, { target: { value: 'Tudo certo!' } });
    fireEvent.submit(campo.closest('form')!);

    await waitFor(() =>
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            c.url.endsWith('/conv-1/messages') &&
            JSON.parse(c.body as string).body === 'Tudo certo!'
        )
      ).toBe(true)
    );
    expect((campo as HTMLInputElement).value).toBe('');
  });

  it('nao envia mensagem em branco', async () => {
    mockApi({ conversations: [conversa()], messages: [mensagem()] });

    renderInbox();
    await screen.findByText('Oi, tudo bem?');

    const botaoEnviar = screen.getByRole('button', { name: '' });
    expect(botaoEnviar).toBeDisabled();
  });
});

describe('Inbox — iniciar conversa via ?to=', () => {
  it('abre a conversa do usuario indicado na querystring', async () => {
    mockApi({
      conversations: [],
      messages: [],
      onStart: () => conversa({ id: 'conv-novo' }),
    });

    renderInbox('/messages?to=scout-1');

    await waitFor(() =>
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            c.url.endsWith('/messages/conversations') &&
            JSON.parse(c.body as string).recipient_id === 'scout-1'
        )
      ).toBe(true)
    );

    // Aparece na barra lateral (a conversa nova entra na lista) e no cabecalho
    // (ela ja abre selecionada) -- por isso duas ocorrencias, nao uma.
    await waitFor(() => expect(screen.getAllByText('Ana Souza')).toHaveLength(2));
  });
});

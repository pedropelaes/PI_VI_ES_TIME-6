import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Feed from './feed';

function item(id: string, overrides: Record<string, unknown> = {}) {
  return {
    id,
    file_url: `/uploads/clips/job/${id}.mp4`,
    duration_seconds: 8,
    published_at: '2026-10-27T17:00:00',
    like_count: 0,
    liked_by_me: false,
    athlete: {
      user_id: 'abc',
      first_name: 'Jeh',
      last_name: 'Rodrigues',
      avatar_url: null,
      position: 'ATACANTE',
      age: 19,
      city: 'Campinas',
      state: 'SP',
      status: 'DISPONIVEL',
    },
    ...overrides,
  };
}

function json(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

/** Guarda as URLs pedidas para os testes conferirem filtros e cursor. */
function mockFetch(handler: (url: string, init?: RequestInit) => Promise<Response>) {
  const calls: { url: string; method: string }[] = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
    const url = typeof input === 'string' ? input : input.toString();
    calls.push({ url, method: init?.method ?? 'GET' });
    return handler(url, init);
  });
  return calls;
}

function renderFeed() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Feed />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('Feed', () => {
  it('mostra o clipe com nome do atleta linkando para o perfil', async () => {
    mockFetch(() => json({ items: [item('c1')], next_cursor: null }));

    renderFeed();

    const nome = await screen.findByRole('link', { name: 'Jeh Rodrigues' });
    expect(nome).toHaveAttribute('href', '/athletes/abc');
    expect(screen.getByText(/Atacante · 19 anos · Campinas\/SP/)).toBeInTheDocument();
    expect(screen.getByText('Disponível para clube', { selector: '.ai-tags span' })).toBeInTheDocument();
  });

  it('mostra estado vazio quando ninguem publicou', async () => {
    mockFetch(() => json({ items: [], next_cursor: null }));

    renderFeed();

    expect(await screen.findByText('Nenhum lance publicado ainda.')).toBeInTheDocument();
  });

  it('mostra erro com opcao de tentar de novo', async () => {
    mockFetch(() => json({ detail: 'Falhou geral' }, 500));

    renderFeed();

    expect(await screen.findByText('Falhou geral')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Tentar novamente/ })).toBeInTheDocument();
  });

  it('filtro de posicao vai para a API', async () => {
    const calls = mockFetch(() => json({ items: [], next_cursor: null }));
    renderFeed();
    await screen.findByText('Nenhum lance publicado ainda.');

    fireEvent.click(screen.getByRole('button', { name: 'Goleiros' }));

    await screen.findByText('Nenhum lance encontrado com esse filtro.');
    expect(calls.some((c) => c.url.includes('position=GOLEIRO'))).toBe(true);
  });

  it('Sub-20 filtra ate 19 anos', async () => {
    const calls = mockFetch(() => json({ items: [], next_cursor: null }));
    renderFeed();
    await screen.findByText('Nenhum lance publicado ainda.');

    fireEvent.click(screen.getByRole('button', { name: 'Sub-20' }));

    await waitFor(() => expect(calls.some((c) => c.url.includes('max_age=19'))).toBe(true));
  });

  it('carregar mais usa o cursor da pagina anterior', async () => {
    const calls = mockFetch((url) =>
      url.includes('cursor=prox')
        ? json({ items: [item('c2')], next_cursor: null })
        : json({ items: [item('c1')], next_cursor: 'prox' })
    );
    renderFeed();

    fireEvent.click(await screen.findByRole('button', { name: 'Carregar mais' }));

    await waitFor(() => expect(screen.getAllByRole('article')).toHaveLength(2));
    expect(calls.some((c) => c.url.includes('cursor=prox'))).toBe(true);
    expect(screen.queryByRole('button', { name: 'Carregar mais' })).not.toBeInTheDocument();
  });

  it('curtir atualiza o contador e chama a API', async () => {
    const calls = mockFetch((url, init) => {
      if (url.includes('/like') && init?.method === 'POST') {
        return json({ clip_id: 'c1', like_count: 1, liked_by_me: true });
      }
      return json({ items: [item('c1')], next_cursor: null });
    });
    renderFeed();

    fireEvent.click(await screen.findByRole('button', { name: 'Curtir clipe' }));

    const botao = await screen.findByRole('button', { name: 'Descurtir clipe' });
    expect(botao).toHaveTextContent('1');
    expect(calls.some((c) => c.method === 'POST' && c.url.endsWith('/feed/clips/c1/like'))).toBe(true);
  });

  it('curtida que falha volta ao estado anterior', async () => {
    // Segura a resposta do POST para dar tempo de ver o estado otimista.
    let falhar: () => void = () => {};
    mockFetch((url, init) => {
      if (init?.method === 'POST') {
        return new Promise((resolve) => {
          falhar = () => resolve(new Response(JSON.stringify({ detail: 'erro' }), { status: 500 }));
        });
      }
      return json({ items: [item('c1')], next_cursor: null });
    });
    renderFeed();

    fireEvent.click(await screen.findByRole('button', { name: 'Curtir clipe' }));

    // Otimista: muda na hora...
    expect(await screen.findByRole('button', { name: 'Descurtir clipe' })).toHaveTextContent('1');
    falhar();
    // ...e volta quando a API falha.
    await waitFor(() => expect(screen.getByRole('button', { name: 'Curtir clipe' })).toHaveTextContent('0'));
  });
});

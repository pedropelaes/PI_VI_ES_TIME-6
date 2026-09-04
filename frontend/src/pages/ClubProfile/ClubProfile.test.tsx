import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ClubProfile from './ClubProfile';

const DTO = {
  user_id: 'club-1',
  first_name: 'Clube',
  last_name: 'Atletico',
  legal_name: 'Clube Atletico Ltda',
  cnpj: '12345678000195',
  categories: ['SUB_15', 'PROFISSIONAL'],
  city: 'Campinas',
  state: 'SP',
  bio: 'Formando atletas desde 1950.',
  avatar_url: null,
};

/** Mesmo casamento de rota usado no App: /clubs/:userId. */
function renderProfile() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/clubs/club-1']}>
        <Routes>
          <Route path="/clubs/:userId" element={<ClubProfile />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe('ClubProfile', () => {
  it('mostra o estado de carregando enquanto a requisicao esta em voo', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}));

    renderProfile();

    expect(screen.getByText('Carregando perfil...')).toBeInTheDocument();
  });

  it('mostra clube nao encontrado no 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Clube nao encontrado.' }), { status: 404 })
    );

    renderProfile();

    expect(await screen.findByText('Clube nao encontrado.')).toBeInTheDocument();
  });

  it('mostra o erro generico no 500, e nao a mensagem de nao encontrado', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'boom' }), { status: 500 })
    );

    renderProfile();

    await waitFor(() =>
      expect(screen.getByText(/Nao foi possivel carregar o perfil/)).toBeInTheDocument()
    );
    expect(screen.queryByText('Clube nao encontrado.')).not.toBeInTheDocument();
  });

  it('mostra razao social, CNPJ formatado e categorias quando o perfil carrega', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    renderProfile();

    expect(await screen.findByText('Clube Atletico')).toBeInTheDocument();
    expect(screen.getByText('Clube Atletico Ltda')).toBeInTheDocument();
    expect(screen.getByText('12.345.678/0001-95')).toBeInTheDocument();
    expect(screen.getByText('Sub-15')).toBeInTheDocument();
    expect(screen.getByText('Profissional')).toBeInTheDocument();
  });

  it('avisa quando o clube nao informou categorias, em vez de deixar o bloco vazio', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ...DTO, categories: [] }), { status: 200 })
    );

    renderProfile();

    expect(await screen.findByText('Nenhuma categoria informada')).toBeInTheDocument();
  });

  it('nao mostra conteudo de atleta, que nao existe para clube', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    renderProfile();

    await screen.findByText('Clube Atletico');
    expect(screen.queryByText('Clipes Gerados IA')).not.toBeInTheDocument();
    expect(screen.queryByText('Pe Dominante')).not.toBeInTheDocument();
  });
});

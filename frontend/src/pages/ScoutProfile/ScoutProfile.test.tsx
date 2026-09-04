import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ScoutProfile from './ScoutProfile';

const DTO = {
  user_id: 'scout-1',
  first_name: 'Ana',
  last_name: 'Souza',
  organization: 'Cruzeiro',
  credential: 'CBF-1234',
  city: 'Belo Horizonte',
  state: 'MG',
  bio: 'Observadora de base ha 10 anos.',
  avatar_url: null,
};

/** Mesmo casamento de rota usado no App: /scouts/:userId. */
function renderProfile() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/scouts/scout-1']}>
        <Routes>
          <Route path="/scouts/:userId" element={<ScoutProfile />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe('ScoutProfile', () => {
  it('mostra o estado de carregando enquanto a requisicao esta em voo', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}));

    renderProfile();

    expect(screen.getByText('Carregando perfil...')).toBeInTheDocument();
  });

  it('mostra scout nao encontrado no 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Scout nao encontrado.' }), { status: 404 })
    );

    renderProfile();

    expect(await screen.findByText('Scout nao encontrado.')).toBeInTheDocument();
  });

  it('mostra o erro generico no 500, e nao a mensagem de nao encontrado', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'boom' }), { status: 500 })
    );

    renderProfile();

    await waitFor(() =>
      expect(screen.getByText(/Nao foi possivel carregar o perfil/)).toBeInTheDocument()
    );
    expect(screen.queryByText('Scout nao encontrado.')).not.toBeInTheDocument();
  });

  it('mostra nome, organizacao e credencial quando o perfil carrega', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    renderProfile();

    expect(await screen.findByText('Ana Souza')).toBeInTheDocument();
    expect(screen.getByText('Cruzeiro')).toBeInTheDocument();
    expect(screen.getByText('CBF-1234')).toBeInTheDocument();
    expect(screen.getByText('Observadora de base ha 10 anos.')).toBeInTheDocument();
  });

  it('nao mostra conteudo de atleta, que nao existe para scout', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    renderProfile();

    await screen.findByText('Ana Souza');
    expect(screen.queryByText('Clipes Gerados IA')).not.toBeInTheDocument();
    expect(screen.queryByText('Altura')).not.toBeInTheDocument();
  });

  it('usa o texto neutro quando o scout nao escreveu bio', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ...DTO, bio: null }), { status: 200 })
    );

    renderProfile();

    expect(
      await screen.findByText('Este scout ainda nao escreveu uma bio.')
    ).toBeInTheDocument();
  });
});

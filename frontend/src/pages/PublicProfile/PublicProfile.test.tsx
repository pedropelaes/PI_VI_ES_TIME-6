import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import PublicProfile from './PublicProfile';

const DTO = {
  user_id: 'abc',
  first_name: 'Jeh',
  last_name: 'Rodrigues',
  position: 'ATACANTE',
  status: 'DISPONIVEL',
  age: 19,
  height_cm: 178,
  dominant_foot: 'DESTRO',
  city: 'Campinas',
  state: 'SP',
  current_club: null,
  bio: null,
  avatar_url: null,
  clips_count: 42,
};

/**
 * A pagina le o id da rota, entao o teste precisa do mesmo casamento de rota
 * usado no App: /athletes/:userId.
 */
function renderProfile() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/athletes/abc']}>
        <Routes>
          <Route path="/athletes/:userId" element={<PublicProfile />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe('PublicProfile', () => {
  it('mostra o estado de carregando enquanto a requisicao esta em voo', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}));

    renderProfile();

    expect(screen.getByText('Carregando perfil...')).toBeInTheDocument();
  });

  it('mostra atleta nao encontrado no 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Atleta não encontrado.' }), { status: 404 })
    );

    renderProfile();

    expect(await screen.findByText('Atleta não encontrado.')).toBeInTheDocument();
  });

  it('mostra nome e altura formatada quando o perfil carrega', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    renderProfile();

    expect(await screen.findByText('Jeh Rodrigues')).toBeInTheDocument();
    expect(screen.getByText('1,78 m')).toBeInTheDocument();
  });

  it('mostra os numeros do atleta, que sao especificos do papel', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    renderProfile();

    await screen.findByText('Jeh Rodrigues');
    expect(screen.getByText('Clipes Gerados IA')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('Atacante')).toBeInTheDocument();
  });

  it('usa o texto neutro quando o atleta nao escreveu bio', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    renderProfile();

    expect(
      await screen.findByText('Este atleta ainda não escreveu uma bio.')
    ).toBeInTheDocument();
  });

  it('mostra o erro generico no 500, e nao a mensagem de nao encontrado', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'boom' }), { status: 500 })
    );

    renderProfile();

    await waitFor(() =>
      expect(screen.getByText(/Não foi possível carregar o perfil/)).toBeInTheDocument()
    );
    expect(screen.queryByText('Atleta não encontrado.')).not.toBeInTheDocument();
  });
});

describe('PublicProfile — avatar', () => {
  it('mostra a foto do atleta quando ha avatar', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ ...DTO, avatar_url: '/uploads/avatars/abc.png' }),
        { status: 200 }
      )
    );

    renderProfile();

    const imagem = await screen.findByAltText('Foto de perfil de Jeh Rodrigues');
    expect(imagem.getAttribute('src')).toContain('/uploads/avatars/abc.png');
  });

  it('cai para a inicial do nome quando nao ha avatar', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    renderProfile();

    await screen.findByText('Jeh Rodrigues');
    expect(screen.queryByAltText('Foto de perfil de Jeh Rodrigues')).not.toBeInTheDocument();
    expect(screen.getByText('J')).toBeInTheDocument();
  });
});

describe('PublicProfile — atalho de edicao', () => {
  function entrarComo(id: string) {
    localStorage.setItem(
      'user',
      JSON.stringify({ id, email: 'a@b.c', first_name: 'Jeh', last_name: 'Rodrigues', role: 'ATHLETE' })
    );
  }

  it('oferece "Editar perfil" para o dono do perfil', async () => {
    // O id da rota e "abc": o dono e quem tem esse mesmo id na sessao.
    entrarComo('abc');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    renderProfile();

    expect(await screen.findByRole('link', { name: /Editar perfil/ })).toHaveAttribute(
      'href',
      '/profiles/me/edit'
    );
  });

  it('nao oferece "Editar perfil" para visitante', async () => {
    entrarComo('outro-usuario');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    renderProfile();

    await screen.findByText('Jeh Rodrigues');
    expect(screen.queryByText(/Editar perfil/)).not.toBeInTheDocument();
  });

  it('nao oferece "Editar perfil" quando nao ha sessao gravada', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    renderProfile();

    await screen.findByText('Jeh Rodrigues');
    expect(screen.queryByText(/Editar perfil/)).not.toBeInTheDocument();
  });
});

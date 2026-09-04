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
  club_history: null,
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

/**
 * A pagina dispara dois GETs distintos (perfil e clipes), entao o mock de
 * `fetch` precisa responder cada rota com um corpo proprio — um unico
 * `mockResolvedValue` faria o clipe receber o DTO do perfil (nao e array) e
 * quebrar `useAthleteClips`. Por padrao a rota de clipes devolve lista vazia:
 * os testes que nao sao sobre a aba de clipes nao precisam se preocupar com ela.
 */
function mockFetch(
  profileBody: unknown,
  options: { profileStatus?: number; clips?: unknown[] } = {}
) {
  const { profileStatus = 200, clips = [] } = options;

  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = typeof input === 'string' ? input : input.toString();

    if (url.includes('/clips/athletes/')) {
      return Promise.resolve(new Response(JSON.stringify(clips), { status: 200 }));
    }

    return Promise.resolve(new Response(JSON.stringify(profileBody), { status: profileStatus }));
  });
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
    mockFetch({ detail: 'Atleta não encontrado.' }, { profileStatus: 404 });

    renderProfile();

    expect(await screen.findByText('Atleta não encontrado.')).toBeInTheDocument();
  });

  it('mostra nome e altura formatada quando o perfil carrega', async () => {
    mockFetch(DTO);

    renderProfile();

    expect(await screen.findByText('Jeh Rodrigues')).toBeInTheDocument();
    expect(screen.getByText('1,78 m')).toBeInTheDocument();
  });

  it('mostra os numeros do atleta, que sao especificos do papel', async () => {
    mockFetch(DTO);

    renderProfile();

    await screen.findByText('Jeh Rodrigues');
    expect(screen.getByText('Clipes Gerados IA')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('Atacante')).toBeInTheDocument();
  });

  it('usa o texto neutro quando o atleta nao escreveu bio', async () => {
    mockFetch(DTO);

    renderProfile();

    expect(
      await screen.findByText('Este atleta ainda não escreveu uma bio.')
    ).toBeInTheDocument();
  });

  it('mostra o erro generico no 500, e nao a mensagem de nao encontrado', async () => {
    mockFetch({ detail: 'boom' }, { profileStatus: 500 });

    renderProfile();

    await waitFor(() =>
      expect(screen.getByText(/Não foi possível carregar o perfil/)).toBeInTheDocument()
    );
    expect(screen.queryByText('Atleta não encontrado.')).not.toBeInTheDocument();
  });
});

describe('PublicProfile — avatar', () => {
  it('mostra a foto do atleta quando ha avatar', async () => {
    mockFetch({ ...DTO, avatar_url: '/uploads/avatars/abc.png' });

    renderProfile();

    const imagem = await screen.findByAltText('Foto de perfil de Jeh Rodrigues');
    expect(imagem.getAttribute('src')).toContain('/uploads/avatars/abc.png');
  });

  it('cai para a inicial do nome quando nao ha avatar', async () => {
    mockFetch(DTO);

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
    mockFetch(DTO);

    renderProfile();

    expect(await screen.findByRole('link', { name: /Editar perfil/ })).toHaveAttribute(
      'href',
      '/profiles/me/edit'
    );
  });

  it('nao oferece "Editar perfil" para visitante', async () => {
    entrarComo('outro-usuario');
    mockFetch(DTO);

    renderProfile();

    await screen.findByText('Jeh Rodrigues');
    expect(screen.queryByText(/Editar perfil/)).not.toBeInTheDocument();
  });

  it('nao oferece "Editar perfil" quando nao ha sessao gravada', async () => {
    mockFetch(DTO);

    renderProfile();

    await screen.findByText('Jeh Rodrigues');
    expect(screen.queryByText(/Editar perfil/)).not.toBeInTheDocument();
  });
});

describe('PublicProfile — aba de clipes', () => {
  function entrarComo(id: string) {
    localStorage.setItem(
      'user',
      JSON.stringify({ id, email: 'a@b.c', first_name: 'Jeh', last_name: 'Rodrigues', role: 'ATHLETE' })
    );
  }

  it('rotula a aba como "Seus clipes" para o dono do perfil', async () => {
    // O id da rota e "abc": o dono e quem tem esse mesmo id na sessao.
    entrarComo('abc');
    mockFetch(DTO);

    renderProfile();

    expect(await screen.findByText('Seus clipes')).toBeInTheDocument();
    expect(screen.queryByText('Clipes')).not.toBeInTheDocument();
  });

  it('rotula a aba como "Clipes" para um visitante', async () => {
    entrarComo('outro-usuario');
    mockFetch(DTO);

    renderProfile();

    await screen.findByText('Jeh Rodrigues');
    expect(screen.getByText('Clipes')).toBeInTheDocument();
    expect(screen.queryByText('Seus clipes')).not.toBeInTheDocument();
  });

  it('mostra o estado vazio quando o atleta nao tem clipes', async () => {
    mockFetch(DTO, { clips: [] });

    renderProfile();

    expect(
      await screen.findByText('Este atleta ainda não publicou clipes.')
    ).toBeInTheDocument();
  });

  it('mostra os clipes quando ha dados', async () => {
    mockFetch(DTO, {
      clips: [
        {
          id: 'clip-1',
          duration_seconds: 65,
          file_url: '/uploads/clips/job-1/clip-1.mp4',
          created_at: '2026-09-01T10:00:00Z',
        },
      ],
    });

    renderProfile();

    expect(await screen.findByText('1:05')).toBeInTheDocument();
  });
});

describe('PublicProfile — histórico de clubes', () => {
  it('mostra o historico quando o atleta escreveu', async () => {
    mockFetch({
      ...DTO,
      club_history: 'Base - Clube Local (2022-2024)\nSub-20 - Regional FC (2024-2025)',
    });

    renderProfile();

    expect(await screen.findByText('Histórico de Clubes')).toBeInTheDocument();
    // O normalizer padrao da testing-library colapsa \n em espaco antes de
    // comparar, o que esconderia uma regressao que juntasse as linhas. Por
    // isso a comparacao aqui desliga o normalizer e casa o texto literal,
    // \n incluso, contra o que o navegador realmente vai exibir.
    expect(
      screen.getByText(
        'Base - Clube Local (2022-2024)\nSub-20 - Regional FC (2024-2025)',
        { normalizer: (text) => text }
      )
    ).toBeInTheDocument();
  });

  it('nao mostra nada relacionado a historico quando o campo e nulo', async () => {
    mockFetch(DTO);

    renderProfile();

    await screen.findByText('Jeh Rodrigues');
    expect(screen.queryByText('Histórico de Clubes')).not.toBeInTheDocument();
  });
});

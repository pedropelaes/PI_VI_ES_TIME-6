import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import EditProfile from './EditProfile';

const ATHLETE_ME = {
  role: 'ATHLETE',
  profile: {
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
  },
};

const SCOUT_ME = {
  role: 'SCOUT',
  profile: {
    user_id: 'def',
    first_name: 'Marina',
    last_name: 'Alves',
    organization: 'Olheiros FC',
    credential: null,
    city: 'Santos',
    state: 'SP',
    bio: null,
    avatar_url: null,
  },
};

const CLUB_ME = {
  role: 'CLUB',
  profile: {
    user_id: 'ghi',
    first_name: 'Clube',
    last_name: 'Atletico',
    legal_name: 'Clube Atlético LTDA',
    cnpj: '12345678000190',
    categories: ['SUB_17'],
    city: 'Campinas',
    state: 'SP',
    bio: null,
    avatar_url: null,
  },
};

interface Call {
  url: string;
  method: string;
  body: unknown;
}

let calls: Call[];

/**
 * Roteia o fetch por metodo: o GET carrega o perfil e o PUT/POST recebem o que
 * a tela decidiu enviar. Nenhum teste toca a API real.
 */
function mockApi(me: unknown, respostaDeEscrita?: () => Response) {
  return vi
    .spyOn(globalThis, 'fetch')
    .mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      calls.push({ url, method, body: init?.body });

      if (method === 'GET') {
        return new Response(JSON.stringify(me), { status: 200 });
      }

      if (respostaDeEscrita) {
        return respostaDeEscrita();
      }

      return new Response(JSON.stringify(me), { status: 200 });
    });
}

function renderEdit() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/profiles/me/edit']}>
        <EditProfile />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function writeCalls(): Call[] {
  return calls.filter((call) => call.method !== 'GET');
}

beforeEach(() => {
  calls = [];
});

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe('EditProfile — estados da pagina', () => {
  it('mostra o estado de carregando enquanto o perfil nao chega', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}));

    renderEdit();

    expect(screen.getByText('Carregando perfil...')).toBeInTheDocument();
  });

  it('mostra erro quando o perfil nao carrega', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'boom' }), { status: 500 })
    );

    renderEdit();

    expect(
      await screen.findByText(/Não foi possível carregar o seu perfil/)
    ).toBeInTheDocument();
  });
});

describe('EditProfile — formulario por papel', () => {
  it('renderiza os campos do atleta, inclusive o historico de clubes', async () => {
    mockApi(ATHLETE_ME);

    renderEdit();

    expect(await screen.findByLabelText('Histórico de clubes')).toBeInTheDocument();
    expect(screen.getByLabelText('Posição')).toBeInTheDocument();
    expect(screen.getByLabelText('Altura (cm)')).toHaveValue(178);
    expect(screen.getByLabelText('Cidade')).toHaveValue('Campinas');
  });

  it('renderiza os campos do scout, e nao os do atleta', async () => {
    mockApi(SCOUT_ME);

    renderEdit();

    expect(await screen.findByLabelText('Organização')).toBeInTheDocument();
    expect(screen.getByLabelText('Credencial')).toBeInTheDocument();
    expect(screen.queryByLabelText('Posição')).not.toBeInTheDocument();
  });

  it('renderiza os campos do clube, com as categorias marcadas', async () => {
    mockApi(CLUB_ME);

    renderEdit();

    expect(await screen.findByLabelText('Razão social')).toBeInTheDocument();
    expect(screen.getByLabelText('Sub-17')).toBeChecked();
    expect(screen.getByLabelText('Sub-20')).not.toBeChecked();
  });
});

describe('EditProfile — salvamento parcial', () => {
  it('envia apenas o campo alterado', async () => {
    mockApi(ATHLETE_ME);

    renderEdit();

    fireEvent.change(await screen.findByLabelText('Cidade'), {
      target: { value: 'Santos' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }));

    await waitFor(() => expect(writeCalls()).toHaveLength(1));
    const [put] = writeCalls();
    expect(put.method).toBe('PUT');
    expect(JSON.parse(String(put.body))).toEqual({ city: 'Santos' });
  });

  it('nao envia os campos em que o usuario nao tocou', async () => {
    mockApi(ATHLETE_ME);

    renderEdit();

    fireEvent.change(await screen.findByLabelText('Bio'), {
      target: { value: 'Atacante canhoto de Campinas.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }));

    await waitFor(() => expect(writeCalls()).toHaveLength(1));
    expect(Object.keys(JSON.parse(String(writeCalls()[0].body)))).toEqual(['bio']);
  });

  it('depois de salvar, a resposta vira a nova base: salvar de novo nao reenvia', async () => {
    // A resposta do PUT entra no cache e substitui o `initial` do formulario.
    mockApi(
      {
        ...ATHLETE_ME,
        profile: { ...ATHLETE_ME.profile, city: 'Santos' },
      }
    );

    renderEdit();

    fireEvent.change(await screen.findByLabelText('Cidade'), {
      target: { value: 'Santos' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }));

    await screen.findByText('Perfil atualizado com sucesso.');
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }));

    await waitFor(() => expect(writeCalls()).toHaveLength(2));
    expect(JSON.parse(String(writeCalls()[1].body))).toEqual({});
  });

  it('confirma o sucesso do salvamento', async () => {
    mockApi(ATHLETE_ME);

    renderEdit();

    fireEvent.change(await screen.findByLabelText('Cidade'), {
      target: { value: 'Santos' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }));

    expect(await screen.findByText('Perfil atualizado com sucesso.')).toBeInTheDocument();
  });

  it('mostra o erro do servidor em vez de fingir que salvou', async () => {
    mockApi(
      ATHLETE_ME,
      () => new Response(JSON.stringify({ detail: 'Altura inválida.' }), { status: 422 })
    );

    renderEdit();

    fireEvent.change(await screen.findByLabelText('Altura (cm)'), {
      target: { value: '999' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }));

    expect(await screen.findByText(/Altura inválida/)).toBeInTheDocument();
    expect(screen.queryByText('Perfil atualizado com sucesso.')).not.toBeInTheDocument();
  });
});

describe('EditProfile — avatar', () => {
  function escolherArquivo(file: File) {
    fireEvent.change(screen.getByLabelText('Escolher foto de perfil'), {
      target: { files: [file] },
    });
  }

  it('recusa formato invalido sem chamar a API', async () => {
    mockApi(ATHLETE_ME);

    renderEdit();
    await screen.findByLabelText('Cidade');

    escolherArquivo(new File(['x'], 'foto.gif', { type: 'image/gif' }));

    expect(
      await screen.findByText('Formato não suportado. Envie uma imagem JPEG, PNG ou WebP.')
    ).toBeInTheDocument();
    expect(writeCalls()).toHaveLength(0);
  });

  it('recusa arquivo acima de 2 MB sem chamar a API', async () => {
    mockApi(ATHLETE_ME);

    renderEdit();
    await screen.findByLabelText('Cidade');

    escolherArquivo(
      new File([new Uint8Array(2 * 1024 * 1024 + 1)], 'foto.png', { type: 'image/png' })
    );

    expect(
      await screen.findByText('Imagem muito grande. O limite é de 2 MB.')
    ).toBeInTheDocument();
    expect(writeCalls()).toHaveLength(0);
  });

  it('envia o arquivo valido como multipart no campo file', async () => {
    mockApi(ATHLETE_ME);

    renderEdit();
    await screen.findByLabelText('Cidade');

    escolherArquivo(new File(['x'], 'foto.png', { type: 'image/png' }));

    await waitFor(() => expect(writeCalls()).toHaveLength(1));
    const [post] = writeCalls();
    expect(post.method).toBe('POST');
    expect(post.url).toContain('/profiles/me/avatar');
    expect((post.body as FormData).get('file')).toBeInstanceOf(File);
  });

  it('mostra a imagem e o botao de remover quando ja existe avatar', async () => {
    mockApi({
      ...ATHLETE_ME,
      profile: { ...ATHLETE_ME.profile, avatar_url: '/uploads/avatars/abc.png' },
    });

    renderEdit();

    const imagem = await screen.findByAltText('Foto de perfil de Jeh Rodrigues');
    expect(imagem.getAttribute('src')).toContain('/uploads/avatars/abc.png');
    expect(screen.getByRole('button', { name: /Remover foto/ })).toBeInTheDocument();
  });

  it('nao oferece remocao quando nao ha avatar', async () => {
    mockApi(ATHLETE_ME);

    renderEdit();
    await screen.findByLabelText('Cidade');

    expect(screen.queryByRole('button', { name: /Remover foto/ })).not.toBeInTheDocument();
  });

  it('remove o avatar pelo DELETE', async () => {
    mockApi(
      {
        ...ATHLETE_ME,
        profile: { ...ATHLETE_ME.profile, avatar_url: '/uploads/avatars/abc.png' },
      },
      () => new Response(null, { status: 204 })
    );

    renderEdit();

    fireEvent.click(await screen.findByRole('button', { name: /Remover foto/ }));

    await waitFor(() => expect(writeCalls()).toHaveLength(1));
    expect(writeCalls()[0].method).toBe('DELETE');
  });
});

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Header } from './Header';
import { MY_PROFILE_QUERY_KEY } from '../../features/profiles/hooks/useMyProfile';

const USUARIO = {
  id: 'abc',
  email: 'ana@exemplo.com',
  first_name: 'Ana',
  last_name: 'Olheira',
  role: 'SCOUT',
  max_clips_allowed: 20,
};

function perfilCom(avatarUrl: string | null) {
  return {
    role: 'SCOUT',
    profile: {
      user_id: 'abc',
      first_name: 'Ana',
      last_name: 'Olheira',
      organization: null,
      credential: null,
      city: null,
      state: null,
      bio: null,
      avatar_url: avatarUrl,
    },
  };
}

function montar(perfil: unknown): { client: QueryClient } {
  // staleTime infinito para o cache ser a unica fonte: sem isso a query refaz o
  // fetch ao montar e sobrescreve o que o teste acabou de escrever. O que se
  // verifica aqui e a reacao a mudanca de cache, nao o carregamento.
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  client.setQueryData(MY_PROFILE_QUERY_KEY, perfil);

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  }

  render(<Header />, { wrapper: Wrapper });
  return { client };
}

beforeEach(() => {
  localStorage.setItem('user', JSON.stringify(USUARIO));
  localStorage.setItem('access_token', 'token');
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(perfilCom(null)), { status: 200 })
  );
});

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe('avatar do header', () => {
  it('mostra a inicial do nome quando nao ha foto', () => {
    montar(perfilCom(null));

    expect(screen.getByText('A')).toBeInTheDocument();
    expect(screen.queryByAltText(/Foto de perfil de Ana Olheira/)).toBeNull();
  });

  it('mostra a foto quando o perfil tem avatar', () => {
    montar(perfilCom('/uploads/avatars/abc.png'));

    const img = screen.getByAltText('Foto de perfil de Ana Olheira');
    // resolveAvatarUrl prefixa com VITE_API_PATH; o teste checa o sufixo para
    // nao amarrar na variavel de ambiente.
    expect(img.getAttribute('src')).toContain('/uploads/avatars/abc.png');
  });

  it('troca a foto quando o cache do proprio perfil muda', async () => {
    // E a razao de o header ler GET /profiles/me em vez do localStorage:
    // o upload escreve nesta chave e o header reage sozinho.
    const { client } = montar(perfilCom(null));
    expect(screen.getByText('A')).toBeInTheDocument();

    client.setQueryData(MY_PROFILE_QUERY_KEY, perfilCom('/uploads/avatars/nova.webp'));

    await waitFor(() => {
      const img = screen.getByAltText('Foto de perfil de Ana Olheira');
      expect(img.getAttribute('src')).toContain('/uploads/avatars/nova.webp');
    });
  });
});

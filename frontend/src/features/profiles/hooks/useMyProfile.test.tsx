import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useMyProfile } from './useMyProfile';

const ME = {
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

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe('useMyProfile', () => {
  it('comeca carregando', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useMyProfile(), { wrapper });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it('devolve o papel e o perfil como vieram da API', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(ME), { status: 200 })
    );

    const { result } = renderHook(() => useMyProfile(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data?.role).toBe('SCOUT');
    expect(result.current.data?.profile.first_name).toBe('Marina');
  });

  it('busca /profiles/me, que descobre o papel pelo JWT', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(ME), { status: 200 })
    );

    const { result } = renderHook(() => useMyProfile(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(String(fetchSpy.mock.calls[0][0])).toContain('/profiles/me');
  });

  it('sinaliza notFound quando o usuario nao tem perfil do seu papel', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Perfil não encontrado.' }), { status: 404 })
    );

    const { result } = renderHook(() => useMyProfile(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.notFound).toBe(true);
    expect(result.current.isError).toBe(true);
  });

  it('sinaliza unauthorized no 401', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'sem token' }), { status: 401 })
    );

    const { result } = renderHook(() => useMyProfile(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.unauthorized).toBe(true);
  });

  it('sinaliza erro generico em falha de servidor', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'boom' }), { status: 500 })
    );

    const { result } = renderHook(() => useMyProfile(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(true);
    expect(result.current.notFound).toBe(false);
  });

  it('nao fica preso em isLoading depois que a requisicao termina', async () => {
    // Mesmo idioma dos hooks por papel: isPending sozinho manteria a tela em
    // "carregando" quando a query esta ociosa.
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(ME), { status: 200 })
    );

    const { result } = renderHook(() => useMyProfile(), { wrapper });

    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.isLoading).toBe(false);
  });
});

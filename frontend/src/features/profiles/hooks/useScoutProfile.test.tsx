import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useScoutProfile } from './useScoutProfile';

const DTO = {
  user_id: 'scout-1',
  first_name: 'Ana',
  last_name: 'Souza',
  organization: 'Cruzeiro',
  credential: 'CBF-1234',
  city: 'Belo Horizonte',
  state: 'MG',
  bio: null,
  avatar_url: null,
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

describe('useScoutProfile', () => {
  it('comeca carregando', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    const { result } = renderHook(() => useScoutProfile('scout-1'), { wrapper });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.profile).toBeUndefined();
  });

  it('devolve o view model ja formatado', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    const { result } = renderHook(() => useScoutProfile('scout-1'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.profile?.fullName).toBe('Ana Souza');
    expect(result.current.profile?.organizationLabel).toBe('Cruzeiro');
    expect(result.current.profile?.location).toBe('Belo Horizonte, MG');
  });

  it('busca a rota de scout, nao a de atleta', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    const { result } = renderHook(() => useScoutProfile('scout-1'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(String(fetchSpy.mock.calls[0][0])).toContain('/profiles/scouts/scout-1');
  });

  it('sinaliza notFound no 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Scout não encontrado.' }), { status: 404 })
    );

    const { result } = renderHook(() => useScoutProfile('scout-1'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.notFound).toBe(true);
  });

  it('sinaliza erro generico em falha de servidor', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'boom' }), { status: 500 })
    );

    const { result } = renderHook(() => useScoutProfile('scout-1'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(true);
    expect(result.current.notFound).toBe(false);
  });

  it('nao busca nem fica preso em isLoading quando o id esta ausente', () => {
    // Com `enabled: false` o React Query permanece `isPending: true` mas
    // `fetchStatus: 'idle'`; sem checar fetchStatus a tela giraria para sempre.
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    const { result } = renderHook(() => useScoutProfile(undefined), { wrapper });

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(result.current.isLoading).toBe(false);
  });
});

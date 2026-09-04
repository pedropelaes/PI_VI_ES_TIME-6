import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useClubProfile } from './useClubProfile';

const DTO = {
  user_id: 'club-1',
  first_name: 'Clube',
  last_name: 'Atletico',
  legal_name: 'Clube Atletico Ltda',
  cnpj: '12345678000195',
  categories: ['SUB_15', 'PROFISSIONAL'],
  city: 'Campinas',
  state: 'SP',
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

describe('useClubProfile', () => {
  it('comeca carregando', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    const { result } = renderHook(() => useClubProfile('club-1'), { wrapper });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.profile).toBeUndefined();
  });

  it('devolve o view model ja formatado', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    const { result } = renderHook(() => useClubProfile('club-1'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.profile?.fullName).toBe('Clube Atletico');
    expect(result.current.profile?.cnpjLabel).toBe('12.345.678/0001-95');
    expect(result.current.profile?.categoryLabels).toEqual(['Sub-15', 'Profissional']);
  });

  it('busca a rota de clube, nao a de atleta', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    const { result } = renderHook(() => useClubProfile('club-1'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(String(fetchSpy.mock.calls[0][0])).toContain('/profiles/clubs/club-1');
  });

  it('sinaliza notFound no 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Clube nao encontrado.' }), { status: 404 })
    );

    const { result } = renderHook(() => useClubProfile('club-1'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.notFound).toBe(true);
  });

  it('sinaliza erro generico em falha de servidor', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'boom' }), { status: 500 })
    );

    const { result } = renderHook(() => useClubProfile('club-1'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(true);
    expect(result.current.notFound).toBe(false);
  });

  it('nao busca nem fica preso em isLoading quando o id esta ausente', () => {
    // Com `enabled: false` o React Query permanece `isPending: true` mas
    // `fetchStatus: 'idle'`; sem checar fetchStatus a tela giraria para sempre.
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    const { result } = renderHook(() => useClubProfile(undefined), { wrapper });

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(result.current.isLoading).toBe(false);
  });
});

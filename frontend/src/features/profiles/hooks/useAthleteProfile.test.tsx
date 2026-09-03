import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useAthleteProfile } from './useAthleteProfile';

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

describe('useAthleteProfile', () => {
  it('comeca carregando', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    const { result } = renderHook(() => useAthleteProfile('abc'), { wrapper });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.profile).toBeUndefined();
  });

  it('devolve o view model ja formatado', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(DTO), { status: 200 })
    );

    const { result } = renderHook(() => useAthleteProfile('abc'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.profile?.fullName).toBe('Jeh Rodrigues');
    expect(result.current.profile?.heightLabel).toBe('1,78 m');
  });

  it('sinaliza notFound no 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Atleta nao encontrado.' }), { status: 404 })
    );

    const { result } = renderHook(() => useAthleteProfile('abc'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.notFound).toBe(true);
  });

  it('sinaliza erro generico em falha de servidor', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'boom' }), { status: 500 })
    );

    const { result } = renderHook(() => useAthleteProfile('abc'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(true);
    expect(result.current.notFound).toBe(false);
  });

  it('nao busca quando o id esta ausente', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    renderHook(() => useAthleteProfile(undefined), { wrapper });

    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('nao fica preso em isLoading quando o id esta ausente', () => {
    // Com `enabled: false` o React Query permanece `isPending: true` (dado
    // ainda nao chegou) mas `fetchStatus: 'idle'` (nada em andamento). Sem
    // checar fetchStatus, isLoading ficaria `true` para sempre nessa tela.
    vi.spyOn(globalThis, 'fetch');

    const { result } = renderHook(() => useAthleteProfile(undefined), { wrapper });

    expect(result.current.isLoading).toBe(false);
  });
});

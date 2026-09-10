import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useAthleteClips } from './useAthleteClips';

const CLIPS = [
  {
    id: 'clip-1',
    duration_seconds: 65,
    file_url: '/uploads/clips/job-1/clip-1.mp4',
    created_at: '2026-09-01T10:00:00Z',
  },
];

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

describe('useAthleteClips', () => {
  it('comeca carregando', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(CLIPS), { status: 200 })
    );

    const { result } = renderHook(() => useAthleteClips('abc'), { wrapper });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.clips).toEqual([]);
  });

  it('devolve os clipes ja formatados', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(CLIPS), { status: 200 })
    );

    const { result } = renderHook(() => useAthleteClips('abc'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.clips).toHaveLength(1);
    expect(result.current.clips[0].durationLabel).toBe('1:05');
    expect(result.current.clips[0].videoUrl).toContain('/uploads/clips/job-1/clip-1.mp4');
  });

  it('devolve lista vazia quando o atleta nao tem clipes', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 })
    );

    const { result } = renderHook(() => useAthleteClips('abc'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.clips).toEqual([]);
    expect(result.current.isError).toBe(false);
  });

  it('sinaliza erro em falha de servidor', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'boom' }), { status: 500 })
    );

    const { result } = renderHook(() => useAthleteClips('abc'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(true);
  });

  it('trata 404 (atleta inexistente) como erro, nao como lista vazia', async () => {
    // GET /profiles/athletes/{id}, que renderiza a mesma pagina, ja devolve 404
    // pra id inexistente ou sem papel de atleta — a rota de clipes segue a
    // mesma regra. Na pratica a aba so aparece depois que o perfil carregou
    // com sucesso, mas o hook nao deve mostrar "sem clipes" pra um atleta que
    // nao existe.
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Atleta não encontrado.' }), { status: 404 })
    );

    const { result } = renderHook(() => useAthleteClips('inexistente'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(true);
    expect(result.current.clips).toEqual([]);
  });

  it('nao busca quando o id esta ausente', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    renderHook(() => useAthleteClips(undefined), { wrapper });

    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('nao fica preso em isLoading quando o id esta ausente', () => {
    // Com `enabled: false` o React Query permanece `isPending: true` (dado
    // ainda nao chegou) mas `fetchStatus: 'idle'` (nada em andamento). Sem
    // checar fetchStatus, isLoading ficaria `true` para sempre nessa tela.
    vi.spyOn(globalThis, 'fetch');

    const { result } = renderHook(() => useAthleteClips(undefined), { wrapper });

    expect(result.current.isLoading).toBe(false);
  });
});

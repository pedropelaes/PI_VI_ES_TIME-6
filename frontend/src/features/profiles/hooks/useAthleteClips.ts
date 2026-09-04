import { useQuery } from '@tanstack/react-query';
import { getAthleteClips } from '../api';
import { toAthleteClipView } from '../mappers';
import type { AthleteClipView } from '../types';

interface UseAthleteClipsResult {
  clips: AthleteClipView[];
  isLoading: boolean;
  isError: boolean;
}

/**
 * Clipes do atleta para a aba "Clipes"/"Seus clipes" do perfil publico. Espelha
 * `useAthleteProfile`: mesmo idioma de `isLoading`, mesma decisao de so buscar
 * quando ha `userId`.
 *
 * Um 404 (id inexistente ou sem papel de atleta) vira `isError`, nao lista
 * vazia — a aba so aparece depois que o perfil carregou com sucesso, entao na
 * pratica isso e quase inalcancavel, mas nao deve exibir "sem clipes" para um
 * atleta que nao existe.
 */
export function useAthleteClips(userId: string | undefined): UseAthleteClipsResult {
  const { data, isPending, isError, fetchStatus } = useQuery({
    queryKey: ['athlete-clips', userId],
    queryFn: () => getAthleteClips(userId as string),
    enabled: Boolean(userId),
  });

  return {
    clips: data ? data.map(toAthleteClipView) : [],
    // Com `enabled: false` o React Query fica pending mas ocioso; sem checar
    // fetchStatus a tela ficaria em "carregando" para sempre quando nao ha id.
    isLoading: isPending && fetchStatus !== 'idle',
    isError,
  };
}

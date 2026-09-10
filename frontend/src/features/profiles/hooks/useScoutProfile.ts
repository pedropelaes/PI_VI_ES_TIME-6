import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../../../shared/lib/httpClient';
import { getScoutProfile } from '../api';
import { toScoutProfileView } from '../mappers';
import type { ScoutProfileView } from '../types';

interface UseScoutProfileResult {
  profile: ScoutProfileView | undefined;
  isLoading: boolean;
  isError: boolean;
  notFound: boolean;
}

export function useScoutProfile(userId: string | undefined): UseScoutProfileResult {
  const { data, isPending, isError, error, fetchStatus } = useQuery({
    queryKey: ['scout-profile', userId],
    queryFn: () => getScoutProfile(userId as string),
    enabled: Boolean(userId),
  });

  return {
    profile: data ? toScoutProfileView(data) : undefined,
    // Com `enabled: false` o React Query fica pending mas ocioso; sem checar
    // fetchStatus a tela ficaria em "carregando" para sempre quando nao ha id.
    isLoading: isPending && fetchStatus !== 'idle',
    isError,
    notFound: error instanceof ApiError && error.notFound,
  };
}

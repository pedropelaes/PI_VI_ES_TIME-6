import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../../../shared/lib/httpClient';
import { getAthleteProfile } from '../api';
import { toAthleteProfileView } from '../mappers';
import type { AthleteProfileView } from '../types';

interface UseAthleteProfileResult {
  profile: AthleteProfileView | undefined;
  isLoading: boolean;
  isError: boolean;
  notFound: boolean;
}

export function useAthleteProfile(userId: string | undefined): UseAthleteProfileResult {
  const { data, isPending, isError, error, fetchStatus } = useQuery({
    queryKey: ['athlete-profile', userId],
    queryFn: () => getAthleteProfile(userId as string),
    enabled: Boolean(userId),
  });

  return {
    profile: data ? toAthleteProfileView(data) : undefined,
    // Com `enabled: false` o React Query fica pending mas ocioso; sem checar
    // fetchStatus a tela ficaria em "carregando" para sempre quando nao ha id.
    isLoading: isPending && fetchStatus !== 'idle',
    isError,
    notFound: error instanceof ApiError && error.notFound,
  };
}

import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../../../shared/lib/httpClient';
import { getClubProfile } from '../api';
import { toClubProfileView } from '../mappers';
import type { ClubProfileView } from '../types';

interface UseClubProfileResult {
  profile: ClubProfileView | undefined;
  isLoading: boolean;
  isError: boolean;
  notFound: boolean;
}

export function useClubProfile(userId: string | undefined): UseClubProfileResult {
  const { data, isPending, isError, error, fetchStatus } = useQuery({
    queryKey: ['club-profile', userId],
    queryFn: () => getClubProfile(userId as string),
    enabled: Boolean(userId),
  });

  return {
    profile: data ? toClubProfileView(data) : undefined,
    // Com `enabled: false` o React Query fica pending mas ocioso; sem checar
    // fetchStatus a tela ficaria em "carregando" para sempre quando nao ha id.
    isLoading: isPending && fetchStatus !== 'idle',
    isError,
    notFound: error instanceof ApiError && error.notFound,
  };
}

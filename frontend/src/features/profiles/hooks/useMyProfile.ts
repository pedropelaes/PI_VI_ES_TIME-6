import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../../../shared/lib/httpClient';
import { getMyProfile } from '../api';
import type { MyProfileDTO } from '../api';

/** Chave unica do perfil do autenticado: salvar e trocar avatar escrevem nela. */
export const MY_PROFILE_QUERY_KEY = ['my-profile'] as const;

interface UseMyProfileResult {
  /** Polimorfico: o narrowing por `role` e feito por quem consome. */
  data: MyProfileDTO | undefined;
  isLoading: boolean;
  isError: boolean;
  notFound: boolean;
  unauthorized: boolean;
}

/**
 * Le `GET /profiles/me`, que devolve `{ role, profile }` conforme o papel do
 * JWT. Previsto na fatia anterior e construido aqui, com a tela de edicao.
 */
export function useMyProfile(): UseMyProfileResult {
  const { data, isPending, isError, error, fetchStatus } = useQuery({
    queryKey: MY_PROFILE_QUERY_KEY,
    queryFn: getMyProfile,
  });

  return {
    data,
    // Mesmo idioma dos demais hooks: com a query ociosa o React Query segue
    // `isPending`, e sem checar fetchStatus a tela ficaria carregando sempre.
    isLoading: isPending && fetchStatus !== 'idle',
    isError,
    notFound: error instanceof ApiError && error.notFound,
    unauthorized: error instanceof ApiError && error.unauthorized,
  };
}

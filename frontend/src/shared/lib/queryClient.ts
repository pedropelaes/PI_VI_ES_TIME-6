import { QueryClient } from '@tanstack/react-query';
import { ApiError } from './httpClient';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // Repetir um 404 ou um 401 e desperdicio: a resposta nao vai mudar.
      retry: (falhas, erro) => {
        if (erro instanceof ApiError && (erro.notFound || erro.unauthorized)) {
          return false;
        }
        return falhas < 2;
      },
    },
  },
});

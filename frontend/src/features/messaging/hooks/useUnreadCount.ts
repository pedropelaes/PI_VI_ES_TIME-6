import { useQuery } from '@tanstack/react-query';
import { getUnreadCount } from '../api';

// So a rede de seguranca: o WebSocket invalida esta query a cada mensagem nova.
const POLL_INTERVAL_MS = 30_000;

export const UNREAD_COUNT_QUERY_KEY = ['messages', 'unread-count'] as const;

/** Total de mensagens nao lidas em todas as conversas, para o badge do header. */
export function useUnreadCount({ enabled = true }: { enabled?: boolean } = {}): number {
  const { data } = useQuery({
    queryKey: UNREAD_COUNT_QUERY_KEY,
    queryFn: getUnreadCount,
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: true,
    enabled,
  });

  return data?.count ?? 0;
}

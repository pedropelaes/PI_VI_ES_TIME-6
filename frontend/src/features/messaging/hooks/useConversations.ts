import { useQuery } from '@tanstack/react-query';
import { getConversations } from '../api';
import { toConversationView } from '../mappers';
import type { ConversationView } from '../types';

export const CONVERSATIONS_QUERY_KEY = ['messages', 'conversations'] as const;

// So a rede de seguranca: o WebSocket (`useMessagingSocket`) invalida esta query
// assim que chega mensagem nova. O poll cobre a janela sem conexao (reconectando).
const POLL_INTERVAL_MS = 30_000;

interface UseConversationsResult {
  conversations: ConversationView[];
  isLoading: boolean;
  isError: boolean;
}

export function useConversations(): UseConversationsResult {
  const { data, isPending, isError, fetchStatus } = useQuery({
    queryKey: CONVERSATIONS_QUERY_KEY,
    queryFn: getConversations,
    refetchInterval: POLL_INTERVAL_MS,
    // Continua sondando com a aba em segundo plano: e assim que o badge do
    // header (`useUnreadCount`) se mantem correto sem o usuario reabrir a aba.
    refetchIntervalInBackground: true,
  });

  return {
    conversations: (data ?? []).map(toConversationView),
    isLoading: isPending && fetchStatus !== 'idle',
    isError,
  };
}

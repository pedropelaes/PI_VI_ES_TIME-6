import { useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '../../../shared/lib/httpClient';
import { getMessages, markConversationRead, sendMessage } from '../api';
import { toMessageView } from '../mappers';
import type { MessageView } from '../types';
import { CONVERSATIONS_QUERY_KEY } from './useConversations';

// So a rede de seguranca: a entrega principal e o WebSocket (`useMessagingSocket`).
// Este poll cobre a janela entre a conexao cair e o reconnect pegar de novo.
const POLL_INTERVAL_MS = 20_000;

export function messagesQueryKey(conversationId: string) {
  return ['messages', 'conversation', conversationId] as const;
}

interface UseConversationMessagesResult {
  messages: MessageView[];
  isLoading: boolean;
  isError: boolean;
  send: (body: string) => void;
  isSending: boolean;
  sendErrorMessage: string | null;
}

/**
 * Mensagens da conversa ativa. A entrega de mensagem nova e o WebSocket
 * (`useMessagingSocket`, escrevendo direto no cache desta query); o polling aqui e
 * so reserva. Marca a conversa como lida sozinho sempre que ela muda ou o total de
 * mensagens aumenta -- por WS ou por poll, tanto faz a origem.
 */
export function useConversationMessages(
  conversationId: string | null,
  myUserId: string | undefined
): UseConversationMessagesResult {
  const queryClient = useQueryClient();
  const enabled = Boolean(conversationId);

  const { data, isPending, isError, fetchStatus } = useQuery({
    queryKey: messagesQueryKey(conversationId ?? ''),
    queryFn: () => getMessages(conversationId as string),
    enabled,
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: true,
  });

  const sendMutation = useMutation({
    mutationFn: (body: string) => sendMessage(conversationId as string, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: messagesQueryKey(conversationId ?? '') });
      queryClient.invalidateQueries({ queryKey: CONVERSATIONS_QUERY_KEY });
    },
  });

  const readMutation = useMutation({
    mutationFn: (id: string) => markConversationRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CONVERSATIONS_QUERY_KEY });
    },
  });

  const totalMensagens = data?.messages.length ?? 0;

  // Reage a troca de conversa e a chegada de mensagens novas (via polling). So a
  // contagem entra nas deps -- reagir ao array inteiro disparia a cada poll, mesmo
  // sem novidade, porque a query devolve uma lista nova a cada resposta.
  useEffect(() => {
    if (!conversationId || totalMensagens === 0) {
      return;
    }
    readMutation.mutate(conversationId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId, totalMensagens]);

  return {
    messages: (data?.messages ?? []).map((m) => toMessageView(m, myUserId ?? '')),
    isLoading: enabled && isPending && fetchStatus !== 'idle',
    isError,
    send: (body: string) => sendMutation.mutate(body),
    isSending: sendMutation.isPending,
    sendErrorMessage:
      sendMutation.error instanceof ApiError ? sendMutation.error.message : null,
  };
}

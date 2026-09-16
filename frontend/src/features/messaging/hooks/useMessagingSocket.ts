import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getToken } from '../../../services/api';
import { wsUrl } from '../../../shared/lib/httpClient';
import type { MessageDTO, MessageListDTO } from '../types';
import { CONVERSATIONS_QUERY_KEY } from './useConversations';
import { messagesQueryKey } from './useConversationMessages';
import { UNREAD_COUNT_QUERY_KEY } from './useUnreadCount';

const RECONNECT_DELAY_MS = 3_000;

type SocketEvent =
  | { type: 'new_message'; message: MessageDTO }
  | { type: 'conversation_read'; conversation_id: string };

/**
 * Canal de entrega em tempo real da Inbox: mantem um WebSocket autenticado aberto e
 * escreve direto no cache do React Query quando chega evento, sem esperar o proximo
 * poll (que continua existindo como rede de seguranca -- ver `useConversations` e
 * `useConversationMessages`).
 */
export function useMessagingSocket(myUserId: string | undefined): void {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!myUserId) {
      return;
    }

    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let desmontado = false;

    function conectar() {
      const token = getToken();
      if (!token || desmontado) {
        return;
      }

      socket = new WebSocket(wsUrl(`/messages/ws?token=${encodeURIComponent(token)}`));

      socket.onmessage = (event) => {
        let dado: SocketEvent;
        try {
          dado = JSON.parse(event.data);
        } catch {
          return;
        }

        if (dado.type === 'new_message') {
          const mensagem = dado.message;
          queryClient.setQueryData<MessageListDTO>(
            messagesQueryKey(mensagem.conversation_id),
            (atual) => {
              // undefined = ninguem esta olhando essa conversa agora: nao ha cache
              // para atualizar, e a lista de conversas abaixo ja cobre o preview.
              if (!atual || atual.messages.some((m) => m.id === mensagem.id)) {
                return atual;
              }
              return { ...atual, messages: [...atual.messages, mensagem] };
            }
          );
          queryClient.invalidateQueries({ queryKey: CONVERSATIONS_QUERY_KEY });
          queryClient.invalidateQueries({ queryKey: UNREAD_COUNT_QUERY_KEY });
        }

        if (dado.type === 'conversation_read') {
          // O outro lado leu: minhas mensagens enviadas nessa conversa viram "lidas"
          // na hora (os dois riscos azuis), sem esperar reabrir a tela.
          queryClient.setQueryData<MessageListDTO>(
            messagesQueryKey(dado.conversation_id),
            (atual) => {
              if (!atual) {
                return atual;
              }
              return {
                ...atual,
                messages: atual.messages.map((m) =>
                  m.sender_id === myUserId && m.read_at === null
                    ? { ...m, read_at: new Date().toISOString() }
                    : m
                ),
              };
            }
          );
        }
      };

      socket.onclose = () => {
        if (desmontado) {
          return;
        }
        // Reconexao simples: a tela continua funcionando pelo polling de reserva
        // enquanto a rede nao volta, so perde a entrega instantanea nesse meio-tempo.
        reconnectTimer = setTimeout(conectar, RECONNECT_DELAY_MS);
      };
    }

    conectar();

    return () => {
      desmontado = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      socket?.close();
    };
  }, [myUserId, queryClient]);
}

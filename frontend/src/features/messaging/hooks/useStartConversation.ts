import { useMutation, useQueryClient } from '@tanstack/react-query';
import { startConversation } from '../api';
import type { ConversationDTO } from '../types';
import { CONVERSATIONS_QUERY_KEY } from './useConversations';

interface UseStartConversationResult {
  start: (recipientId: string) => void;
  isStarting: boolean;
  errorMessage: string | null;
}

/**
 * Abre (ou reaproveita) a conversa com um usuario. Usado pelo botao "Enviar
 * Mensagem" de um perfil e pelo `?to=` da propria Inbox.
 */
export function useStartConversation(
  onStarted: (conversation: ConversationDTO) => void
): UseStartConversationResult {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (recipientId: string) => startConversation(recipientId),
    onSuccess: (conversation) => {
      // Escreve no cache na hora, sem esperar o refetch: senao ha uma janela em que
      // `activeConversationId` ja aponta para a conversa nova mas a lista (de onde a
      // tela le nome/avatar/cabecalho) ainda nao a contem, e o cabecalho renderiza vazio.
      queryClient.setQueryData<ConversationDTO[]>(CONVERSATIONS_QUERY_KEY, (atual) => {
        const lista = atual ?? [];
        const jaExiste = lista.some((c) => c.id === conversation.id);
        return jaExiste
          ? lista.map((c) => (c.id === conversation.id ? conversation : c))
          : [conversation, ...lista];
      });
      queryClient.invalidateQueries({ queryKey: CONVERSATIONS_QUERY_KEY });
      onStarted(conversation);
    },
  });

  return {
    start: mutation.mutate,
    isStarting: mutation.isPending,
    errorMessage: mutation.error ? mutation.error.message : null,
  };
}

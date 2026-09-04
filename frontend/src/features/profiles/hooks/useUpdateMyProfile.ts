import { useMutation, useQueryClient } from '@tanstack/react-query';
import { updateMyProfile } from '../api';
import type { MyProfileDTO } from '../api';
import { MY_PROFILE_QUERY_KEY } from './useMyProfile';

interface UseUpdateMyProfileResult {
  save: (changes: Record<string, unknown>) => void;
  isSaving: boolean;
  isSaved: boolean;
  /** Mensagem do erro de salvamento, ou null. Nunca some sozinha. */
  errorMessage: string | null;
}

/**
 * `PUT /profiles/me` com os campos alterados. A resposta e o perfil atualizado,
 * entao gravamos direto no cache: a tela reflete o que o servidor guardou, nao
 * o que o formulario acha que mandou.
 */
export function useUpdateMyProfile(): UseUpdateMyProfileResult {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (changes: Record<string, unknown>) => updateMyProfile(changes),
    onSuccess: (updated: MyProfileDTO) => {
      queryClient.setQueryData(MY_PROFILE_QUERY_KEY, updated);
    },
  });

  return {
    save: mutation.mutate,
    isSaving: mutation.isPending,
    isSaved: mutation.isSuccess,
    errorMessage: mutation.error ? mutation.error.message : null,
  };
}

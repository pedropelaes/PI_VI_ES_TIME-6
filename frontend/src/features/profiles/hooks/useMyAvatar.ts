import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { deleteMyAvatar, uploadMyAvatar } from '../api';
import type { MyProfileDTO } from '../api';
import { validateAvatarFile } from '../avatarFile';
import { MY_PROFILE_QUERY_KEY } from './useMyProfile';

interface UseMyAvatarResult {
  /** Valida no cliente e so entao envia. Arquivo recusado nao vira requisicao. */
  select: (file: File) => void;
  remove: () => void;
  isBusy: boolean;
  errorMessage: string | null;
}

export function useMyAvatar(): UseMyAvatarResult {
  const queryClient = useQueryClient();
  const [localError, setLocalError] = useState<string | null>(null);

  const upload = useMutation({
    mutationFn: (file: File) => uploadMyAvatar(file),
    onSuccess: (updated: MyProfileDTO) => {
      queryClient.setQueryData(MY_PROFILE_QUERY_KEY, updated);
    },
  });

  const remove = useMutation({
    // O DELETE responde 204 sem corpo, entao nao ha o que gravar no cache:
    // invalidar faz a tela reler o perfil ja sem avatar.
    mutationFn: () => deleteMyAvatar(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MY_PROFILE_QUERY_KEY });
    },
  });

  function select(file: File) {
    const erro = validateAvatarFile(file);

    setLocalError(erro);

    if (erro) {
      return;
    }

    upload.mutate(file);
  }

  return {
    select,
    remove: () => {
      setLocalError(null);
      remove.mutate();
    },
    isBusy: upload.isPending || remove.isPending,
    errorMessage:
      localError ?? upload.error?.message ?? remove.error?.message ?? null,
  };
}

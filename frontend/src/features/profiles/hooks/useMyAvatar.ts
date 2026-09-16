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

/**
 * Acrescenta um parametro de cache-busting ao `avatar_url`.
 *
 * Sem isso, reenviar uma foto com a mesma extensao da anterior (o caso comum)
 * devolve exatamente a mesma URL -- o backend reaproveita a chave
 * `avatars/{user_id}{ext}` (ver comentario em `router.py::upload_my_avatar`).
 * Como a URL nao muda, o React nem toca o atributo `src` do `<img>`, e o
 * navegador continua mostrando a imagem antiga ja decodificada, mesmo com o
 * arquivo novo ja gravado no servidor. So aparece a foto certa depois de um
 * F5, quando a pagina refaz a requisicao do zero.
 */
function comCacheBuster(dto: MyProfileDTO): MyProfileDTO {
  const avatarUrl = dto.profile.avatar_url;

  if (!avatarUrl) {
    return dto;
  }

  const separador = avatarUrl.includes('?') ? '&' : '?';

  return {
    ...dto,
    profile: { ...dto.profile, avatar_url: `${avatarUrl}${separador}t=${Date.now()}` },
  } as MyProfileDTO;
}

export function useMyAvatar(): UseMyAvatarResult {
  const queryClient = useQueryClient();
  const [localError, setLocalError] = useState<string | null>(null);

  const upload = useMutation({
    mutationFn: (file: File) => uploadMyAvatar(file),
    onSuccess: (updated: MyProfileDTO) => {
      queryClient.setQueryData(MY_PROFILE_QUERY_KEY, comCacheBuster(updated));
    },
  });

  // ... resto do arquivo igual

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

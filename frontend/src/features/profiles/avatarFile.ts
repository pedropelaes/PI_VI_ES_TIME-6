/**
 * Validacao de avatar no cliente. Existe para dar erro imediato em vez de
 * esperar o 422 — mas quem decide e o servidor: estes mesmos limites estao na
 * decisao E5 da spec e sao revalidados la.
 */
export const AVATAR_ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'] as const;

export const AVATAR_MAX_BYTES = 2 * 1024 * 1024;

/** Valor do atributo `accept` do input de arquivo. */
export const AVATAR_ACCEPT_ATTR = AVATAR_ACCEPTED_TYPES.join(',');

export const AVATAR_TYPE_ERROR =
  'Formato não suportado. Envie uma imagem JPEG, PNG ou WebP.';

export const AVATAR_SIZE_ERROR = 'Imagem muito grande. O limite é de 2 MB.';

/** Devolve a mensagem de erro, ou null quando o arquivo passa. */
export function validateAvatarFile(file: File): string | null {
  if (!(AVATAR_ACCEPTED_TYPES as readonly string[]).includes(file.type)) {
    return AVATAR_TYPE_ERROR;
  }

  if (file.size > AVATAR_MAX_BYTES) {
    return AVATAR_SIZE_ERROR;
  }

  return null;
}

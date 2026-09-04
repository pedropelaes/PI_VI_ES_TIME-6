import { describe, expect, it } from 'vitest';
import {
  AVATAR_MAX_BYTES,
  AVATAR_SIZE_ERROR,
  AVATAR_TYPE_ERROR,
  validateAvatarFile,
} from './avatarFile';

function fileOf(type: string, bytes: number): File {
  return new File([new Uint8Array(bytes)], 'avatar', { type });
}

describe('validateAvatarFile', () => {
  it('aceita os tres formatos previstos', () => {
    for (const type of ['image/jpeg', 'image/png', 'image/webp']) {
      expect(validateAvatarFile(fileOf(type, 1024))).toBeNull();
    }
  });

  it('recusa formato fora da lista', () => {
    expect(validateAvatarFile(fileOf('image/gif', 1024))).toBe(AVATAR_TYPE_ERROR);
  });

  it('recusa arquivo acima de 2 MB', () => {
    expect(validateAvatarFile(fileOf('image/png', AVATAR_MAX_BYTES + 1))).toBe(
      AVATAR_SIZE_ERROR
    );
  });

  it('aceita arquivo exatamente no limite', () => {
    expect(validateAvatarFile(fileOf('image/png', AVATAR_MAX_BYTES))).toBeNull();
  });

  it('reclama do formato antes do tamanho', () => {
    // Formato errado e o problema mais informativo: trocar o arquivo resolve os
    // dois, e falar de tamanho num GIF confunde.
    expect(validateAvatarFile(fileOf('image/gif', AVATAR_MAX_BYTES + 1))).toBe(
      AVATAR_TYPE_ERROR
    );
  });
});

import { describe, expect, it } from 'vitest';
import { ApiError } from './httpClient';
import { queryClient } from './queryClient';

// A regra de retry e testada aqui porque cada teste de hook monta seu proprio
// QueryClient com `retry: false` (para nao esperar backoff), entao o
// comportamento real do client exportado nunca e exercitado por eles.
describe('queryClient retry', () => {
  const retry = queryClient.getDefaultOptions().queries?.retry as (
    falhas: number,
    erro: unknown
  ) => boolean;

  it('nao tenta de novo em 404', () => {
    expect(retry(0, new ApiError(404, 'nao encontrado'))).toBe(false);
  });

  it('nao tenta de novo em 401', () => {
    expect(retry(0, new ApiError(401, 'nao autorizado'))).toBe(false);
  });

  it('nao tenta de novo em 403 (tambem tratado como unauthorized)', () => {
    expect(retry(0, new ApiError(403, 'proibido'))).toBe(false);
  });

  it('tenta ate 2 vezes em outros erros', () => {
    const erro = new ApiError(500, 'boom');
    expect(retry(0, erro)).toBe(true);
    expect(retry(1, erro)).toBe(true);
    expect(retry(2, erro)).toBe(false);
  });

  it('tenta em erros que nao sao ApiError', () => {
    expect(retry(0, new Error('rede caiu'))).toBe(true);
    expect(retry(2, new Error('rede caiu'))).toBe(false);
  });
});

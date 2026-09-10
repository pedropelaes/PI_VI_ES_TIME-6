import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, httpDelete, httpGet, httpPostForm, httpPut } from './httpClient';

describe('httpClient', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'token-de-teste');
  });

  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('envia o JWT no header Authorization', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );

    await httpGet('/profiles/me');

    const headers = (fetchSpy.mock.calls[0][1]?.headers ?? {}) as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer token-de-teste');
  });

  it('devolve o corpo desserializado', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ city: 'Campinas' }), { status: 200 })
    );

    await expect(httpGet<{ city: string }>('/profiles/me')).resolves.toEqual({
      city: 'Campinas',
    });
  });

  it('lanca ApiError com o status em resposta de erro', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Atleta não encontrado.' }), { status: 404 })
    );

    await expect(httpGet('/profiles/athletes/x')).rejects.toMatchObject({
      status: 404,
      message: 'Atleta não encontrado.',
    });
  });

  it('ApiError expoe notFound para o 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'nao achou' }), { status: 404 })
    );

    const erro = await httpGet('/x').catch((e: unknown) => e);

    if (!(erro instanceof ApiError)) {
      throw new Error('esperava que o erro fosse uma ApiError');
    }
    expect(erro.notFound).toBe(true);
  });

  it('serializa o corpo no PUT', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({}), { status: 200 })
    );

    await httpPut('/profiles/me', { city: 'Santos' });

    expect(fetchSpy.mock.calls[0][1]?.body).toBe('{"city":"Santos"}');
  });

  it('nao envia o header Authorization quando nao ha token', async () => {
    localStorage.clear();
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );

    await httpGet('/profiles/me');

    const headers = (fetchSpy.mock.calls[0][1]?.headers ?? {}) as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it('ApiError expoe unauthorized para 401 e 403', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'sem permissao' }), { status: 401 })
    );
    const erro401 = await httpGet('/x').catch((e: unknown) => e);
    if (!(erro401 instanceof ApiError)) {
      throw new Error('esperava que o erro fosse uma ApiError');
    }
    expect(erro401.unauthorized).toBe(true);

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'proibido' }), { status: 403 })
    );
    const erro403 = await httpGet('/y').catch((e: unknown) => e);
    if (!(erro403 instanceof ApiError)) {
      throw new Error('esperava que o erro fosse uma ApiError');
    }
    expect(erro403.unauthorized).toBe(true);
  });

  it('nao fixa Content-Type no multipart, para o browser definir o boundary', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({}), { status: 200 })
    );
    const form = new FormData();
    form.append('file', new File(['x'], 'a.png', { type: 'image/png' }));

    await httpPostForm('/profiles/me/avatar', form);

    const [, init] = fetchSpy.mock.calls[0];
    const headers = (init?.headers ?? {}) as Record<string, string>;
    expect(headers['Content-Type']).toBeUndefined();
    expect(headers.Authorization).toBe('Bearer token-de-teste');
    expect(init?.body).toBe(form);
  });

  it('faz DELETE com o JWT e aceita 204 sem corpo', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(null, { status: 204 })
    );

    await expect(httpDelete('/profiles/me/avatar')).resolves.toBeUndefined();
    expect(fetchSpy.mock.calls[0][1]?.method).toBe('DELETE');
  });

  it('devolve undefined para resposta 204 sem corpo', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }));

    await expect(httpGet('/profiles/me')).resolves.toBeUndefined();
  });
});

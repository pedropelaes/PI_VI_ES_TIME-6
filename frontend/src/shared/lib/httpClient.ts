/**
 * Cliente HTTP do app: injeta o JWT, aplica timeout e converte erro em ApiError.
 * Primeira peca do F3; services/api.ts segue intacto ate a migracao daquele sub-projeto.
 */
export const API_BASE = import.meta.env.VITE_API_PATH ?? 'http://127.0.0.1:8000/api/v1';
const REQUEST_TIMEOUT_MS = 15000;
const TOKEN_KEY = 'access_token';

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }

  get notFound(): boolean {
    return this.status === 404;
  }

  get unauthorized(): boolean {
    return this.status === 401 || this.status === 403;
  }
}

/**
 * `json: false` e para multipart: quem define o `Content-Type` com o boundary
 * correto e o proprio browser. Fixar `application/json` num FormData faz o
 * servidor receber um corpo que nao consegue desmontar.
 */
function authHeaders(json = true): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  return {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(
  path: string,
  init: RequestInit,
  headers: Record<string, string> = authHeaders()
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
    });

    if (!res.ok) {
      const corpo = await res.json().catch(() => ({}));
      throw new ApiError(res.status, corpo.detail ?? 'Erro inesperado na requisicao.');
    }

    if (res.status === 204) {
      return undefined as T;
    }

    return (await res.json()) as T;
  } finally {
    clearTimeout(timeoutId);
  }
}

export function httpGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'GET' });
}

export function httpPut<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'PUT', body: JSON.stringify(body) });
}

export function httpDelete<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' });
}

/** POST multipart: upload de arquivo, hoje so o avatar. */
export function httpPostForm<T>(path: string, form: FormData): Promise<T> {
  return request<T>(path, { method: 'POST', body: form }, authHeaders(false));
}

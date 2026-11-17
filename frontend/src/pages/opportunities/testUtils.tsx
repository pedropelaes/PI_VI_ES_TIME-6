import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';

export function summary(id: string, over: Record<string, unknown> = {}) {
  return {
    id,
    title: 'Peneira Sub-17',
    mode: 'PRESENCIAL',
    state: 'SP',
    city: 'Campinas',
    event_at: '2026-12-01T12:00:00Z',
    registration_deadline: '2026-11-25T12:00:00Z',
    min_age: 15,
    max_age: 17,
    positions: [],
    spots_left: 10,
    is_cancelled: false,
    organizer: { user_id: 'c1', first_name: 'Guarani', last_name: 'FC', role: 'CLUB', avatar_url: null },
    ...over,
  };
}

export function login(role: 'ATHLETE' | 'CLUB' | 'SCOUT', id = 'u1') {
  localStorage.setItem('access_token', 'tok');
  localStorage.setItem('user', JSON.stringify({ id, email: 'x@x.com', first_name: 'X', last_name: 'Y', role, max_clips_allowed: 20 }));
}

export function json(body: unknown, status = 200) {
  return Promise.resolve(new Response(status === 204 ? null : JSON.stringify(body), { status }));
}

/** Registra as chamadas para os testes conferirem URL e método. */
export function mockFetch(handler: (url: string, method: string) => Promise<Response>) {
  const calls: { url: string; method: string }[] = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
    const url = typeof input === 'string' ? input : input.toString();
    const method = init?.method ?? 'GET';
    calls.push({ url, method });
    return handler(url, method);
  });
  return calls;
}

export function renderAt(path: string, routePath: string, element: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path={routePath} element={element} />
          <Route path="*" element={<p>outra página</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

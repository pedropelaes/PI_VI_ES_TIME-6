import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Opportunities from './Opportunities';
import { json, login, mockFetch, renderAt, summary } from './testUtils';

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

const pagina = { items: [summary('o1'), summary('o2', { title: 'Peneira Online', mode: 'ONLINE', city: null, state: null })], next_cursor: null };

describe('Opportunities', () => {
  it('lista as peneiras e mostra "Publicar peneira" para clube', async () => {
    login('CLUB');
    mockFetch(() => json(pagina));
    renderAt('/opportunities', '/opportunities', <Opportunities />);

    expect(await screen.findByText('Peneira Online')).toBeInTheDocument();
    expect(screen.getByText('Peneira Sub-17')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Publicar peneira' })).toBeInTheDocument();
    expect(screen.queryByLabelText(/elegíveis para mim/i)).not.toBeInTheDocument();
  });

  it('atleta não vê publicar e o filtro de elegíveis vai na query', async () => {
    login('ATHLETE');
    const calls = mockFetch(() => json(pagina));
    renderAt('/opportunities', '/opportunities', <Opportunities />);

    await screen.findByText('Peneira Online');
    expect(screen.queryByRole('link', { name: 'Publicar peneira' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText(/elegíveis para mim/i));
    await waitFor(() => expect(calls.some((c) => c.url.includes('eligible=true'))).toBe(true));
  });

  it('mostra estado vazio', async () => {
    login('ATHLETE');
    mockFetch(() => json({ items: [], next_cursor: null }));
    renderAt('/opportunities', '/opportunities', <Opportunities />);
    expect(await screen.findByText(/nenhuma peneira aberta/i)).toBeInTheDocument();
  });

  it('carrega a próxima página pelo cursor', async () => {
    login('ATHLETE');
    const calls = mockFetch((url) =>
      url.includes('cursor=c2')
        ? json({ items: [summary('o3', { title: 'Terceira' })], next_cursor: null })
        : json({ items: [summary('o1')], next_cursor: 'c2' })
    );
    renderAt('/opportunities', '/opportunities', <Opportunities />);

    fireEvent.click(await screen.findByRole('button', { name: 'Carregar mais' }));
    expect(await screen.findByText('Terceira')).toBeInTheDocument();
    expect(calls.some((c) => c.url.includes('cursor=c2'))).toBe(true);
  });
});

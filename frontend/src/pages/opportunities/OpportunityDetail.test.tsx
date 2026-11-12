import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import OpportunityDetail from './OpportunityDetail';
import { json, login, mockFetch, renderAt, summary } from './testUtils';

function detail(over: Record<string, unknown> = {}) {
  return {
    ...summary('o1'),
    description: 'Avaliação técnica',
    address: 'Rua A, 100',
    meeting_url: null,
    max_applications: 20,
    is_open: true,
    cancelled_at: null,
    my_application: null,
    eligibility: { eligible: true, reason: null },
    ...over,
  };
}

function renderDetail() {
  return renderAt('/opportunities/o1', '/opportunities/:id', <OpportunityDetail />);
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe('OpportunityDetail — atleta', () => {
  it('elegível: inscrever-se chama POST /apply', async () => {
    login('ATHLETE');
    const calls = mockFetch((url, method) =>
      method === 'POST' ? json({ opportunity_id: 'o1', athlete_id: 'u1', status: 'PENDENTE' }, 201) : json(detail())
    );
    renderDetail();

    fireEvent.click(await screen.findByRole('button', { name: 'Inscrever-se' }));
    await waitFor(() =>
      expect(calls.some((c) => c.method === 'POST' && c.url.endsWith('/opportunities/o1/apply'))).toBe(true)
    );
  });

  it('inelegível: botão desabilitado com motivo e link para o perfil', async () => {
    login('ATHLETE');
    mockFetch(() => json(detail({ eligibility: { eligible: false, reason: 'Idade máxima: 17 anos.' } })));
    renderDetail();

    expect(await screen.findByRole('button', { name: 'Inscrever-se' })).toBeDisabled();
    expect(screen.getByText(/Idade máxima: 17 anos/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Editar perfil' })).toHaveAttribute('href', '/profiles/me/edit');
  });

  it('pendente: mostra status e permite cancelar', async () => {
    login('ATHLETE');
    const calls = mockFetch((_url, method) =>
      method === 'DELETE' ? json(null, 204) : json(detail({ my_application: { status: 'PENDENTE' } }))
    );
    renderDetail();

    expect(await screen.findByText('Em análise')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar inscrição' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'DELETE')).toBe(true));
  });

  it('aprovada: mostra o link da avaliação online', async () => {
    login('ATHLETE');
    mockFetch(() =>
      json(detail({ mode: 'ONLINE', my_application: { status: 'APROVADA' }, meeting_url: 'https://meet.example.com/abc' }))
    );
    renderDetail();

    expect(await screen.findByRole('link', { name: 'https://meet.example.com/abc' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancelar inscrição' })).not.toBeInTheDocument();
  });

  it('cancelada: mostra aviso e não deixa se inscrever', async () => {
    login('ATHLETE');
    mockFetch(() => json(detail({ is_cancelled: true, is_open: false })));
    renderDetail();

    expect(await screen.findByText(/foi cancelada pelo organizador/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Inscrever-se' })).not.toBeInTheDocument();
  });
});

describe('OpportunityDetail — dono', () => {
  const inscrito = {
    athlete_id: 'a1', first_name: 'Jeh', last_name: 'Rodrigues', avatar_url: null, position: 'ATACANTE',
    age: 18, city: 'Campinas', state: 'SP', status: 'PENDENTE', created_at: '2026-11-11T12:00:00Z',
  };

  it('vê ações de gestão, lista de inscritos e aprova', async () => {
    login('CLUB', 'c1');
    const calls = mockFetch((url, method) => {
      if (method === 'PATCH') return json({ opportunity_id: 'o1', athlete_id: 'a1', status: 'APROVADA' });
      if (url.endsWith('/applications')) return json([inscrito]);
      return json(detail());
    });
    renderDetail();

    expect(await screen.findByRole('link', { name: 'Editar' })).toHaveAttribute('href', '/opportunities/o1/edit');
    expect(screen.getByRole('button', { name: 'Cancelar peneira' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Apagar' })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'Jeh Rodrigues' })).toHaveAttribute('href', '/athletes/a1');

    fireEvent.click(screen.getByRole('button', { name: 'Aprovar' }));
    await waitFor(() =>
      expect(calls.some((c) => c.method === 'PATCH' && c.url.endsWith('/opportunities/o1/applications/a1'))).toBe(true)
    );
  });

  it('apagar pede confirmação antes de chamar DELETE', async () => {
    login('CLUB', 'c1');
    const calls = mockFetch((url, method) => {
      if (method === 'DELETE') return json(null, 204);
      if (url.endsWith('/applications')) return json([]);
      return json(detail());
    });
    renderDetail();

    fireEvent.click(await screen.findByRole('button', { name: 'Apagar' }));
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false);
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'DELETE')).toBe(true));
  });
});

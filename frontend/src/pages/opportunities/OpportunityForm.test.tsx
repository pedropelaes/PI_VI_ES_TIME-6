import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import OpportunityForm from './OpportunityForm';
import { json, login, mockFetch, renderAt, summary } from './testUtils';

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

function preencher(label: RegExp, valor: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value: valor } });
}

describe('OpportunityForm', () => {
  it('online troca os campos de local pelo link e envia POST', async () => {
    login('CLUB');
    let corpo: Record<string, unknown> = {};
    vi.spyOn(globalThis, 'fetch').mockImplementation((_input, init) => {
      corpo = JSON.parse(String(init?.body));
      return json({ ...summary('novo'), description: 'd' }, 201);
    });
    renderAt('/opportunities/new', '/opportunities/new', <OpportunityForm />);

    preencher(/^título/i, 'Peneira Sub-17');
    preencher(/descrição/i, 'Avaliação');
    fireEvent.change(screen.getByLabelText(/modalidade/i), { target: { value: 'ONLINE' } });
    expect(screen.queryByLabelText(/endereço/i)).not.toBeInTheDocument();
    preencher(/link da reunião/i, 'https://meet.example.com/x');
    preencher(/data do evento/i, '2026-12-01T09:00');
    preencher(/prazo de inscrição/i, '2026-11-25T09:00');
    fireEvent.click(screen.getByLabelText('Goleiro'));
    fireEvent.click(screen.getByRole('button', { name: 'Publicar' }));

    await waitFor(() => expect(corpo.title).toBe('Peneira Sub-17'));
    expect(corpo).toMatchObject({ mode: 'ONLINE', meeting_url: 'https://meet.example.com/x', state: null, positions: ['GOLEIRO'] });
    expect(await screen.findByText('outra página')).toBeInTheDocument(); // navegou para o detalhe
  });

  it('edição pré-preenche e envia PATCH', async () => {
    login('CLUB', 'c1');
    const calls = mockFetch((_url, method) =>
      json({
        ...summary('o1'),
        description: 'Avaliação',
        address: 'Rua A',
        meeting_url: null,
        max_applications: null,
        is_open: true,
        cancelled_at: null,
        my_application: null,
        eligibility: null,
        ...(method === 'PATCH' ? { title: 'Novo título' } : {}),
      })
    );
    renderAt('/opportunities/o1/edit', '/opportunities/:id/edit', <OpportunityForm />);

    expect(await screen.findByDisplayValue('Peneira Sub-17')).toBeInTheDocument();
    preencher(/^título/i, 'Novo título');
    fireEvent.click(screen.getByRole('button', { name: 'Salvar' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'PATCH' && c.url.endsWith('/opportunities/o1'))).toBe(true));
  });

  it('não deixa quem não é o organizador editar', async () => {
    login('CLUB', 'outro');
    mockFetch(() => json({ ...summary('o1'), description: 'd', is_open: true, cancelled_at: null, my_application: null, eligibility: null }));
    renderAt('/opportunities/o1/edit', '/opportunities/:id/edit', <OpportunityForm />);

    expect(await screen.findByText('Esta peneira não pode ser editada.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Salvar' })).not.toBeInTheDocument();
  });
});

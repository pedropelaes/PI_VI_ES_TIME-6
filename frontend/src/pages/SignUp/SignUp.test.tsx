import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import SignUp from './SignUp';

function renderSignUp() {
  return render(
    <MemoryRouter>
      <SignUp />
    </MemoryRouter>
  );
}

function mockRegisterOk() {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({ access_token: 't', token_type: 'bearer', user: {} }), {
      status: 200,
    })
  );
}

function preencherFormulario() {
  fireEvent.change(screen.getByPlaceholderText('Seu nome'), { target: { value: 'Ana' } });
  fireEvent.change(screen.getByPlaceholderText('Seu sobrenome'), { target: { value: 'Souza' } });
  fireEvent.change(screen.getByPlaceholderText('seu-email@email.com'), {
    target: { value: 'ana@x.com' },
  });
  fireEvent.change(screen.getByPlaceholderText('Mínimo 8 caracteres'), {
    target: { value: 'senha12345' },
  });
  fireEvent.change(screen.getByPlaceholderText('Repita a senha'), {
    target: { value: 'senha12345' },
  });
}

function corpoEnviado(fetchSpy: ReturnType<typeof mockRegisterOk>) {
  const init = fetchSpy.mock.calls[0][1] as RequestInit;
  return JSON.parse(String(init.body));
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe('SignUp', () => {
  it('avisa que o papel nao pode mudar depois do cadastro', () => {
    renderSignUp();

    expect(screen.getByText(/não pode ser alterado depois do cadastro/i)).toBeInTheDocument();
  });

  it('oferece os tres papeis habilitados', () => {
    renderSignUp();

    for (const nome of [/Atleta/, /Scout/, /Clube/]) {
      expect(screen.getByRole('radio', { name: nome })).toBeEnabled();
    }
  });

  it('envia ATHLETE por padrao, em MAIUSCULO', async () => {
    const fetchSpy = mockRegisterOk();

    renderSignUp();
    preencherFormulario();
    fireEvent.click(screen.getByRole('button', { name: 'Criar conta' }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    expect(corpoEnviado(fetchSpy).role).toBe('ATHLETE');
  });

  it('envia o papel escolhido pelo usuario', async () => {
    const fetchSpy = mockRegisterOk();

    renderSignUp();
    fireEvent.click(screen.getByRole('radio', { name: /Scout/ }));
    preencherFormulario();
    fireEvent.click(screen.getByRole('button', { name: 'Criar conta' }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    expect(corpoEnviado(fetchSpy).role).toBe('SCOUT');
  });
});

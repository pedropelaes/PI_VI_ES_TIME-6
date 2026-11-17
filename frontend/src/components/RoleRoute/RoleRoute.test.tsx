import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { RoleRoute } from './RoleRoute';

function renderAs(role: string | null) {
  if (role) localStorage.setItem('user', JSON.stringify({ id: 'u1', role }));
  return render(
    <MemoryRouter initialEntries={['/restrito']}>
      <Routes>
        <Route element={<RoleRoute allow={['CLUB', 'SCOUT']} />}>
          <Route path="/restrito" element={<p>conteúdo restrito</p>} />
        </Route>
        <Route path="/opportunities" element={<p>lista</p>} />
      </Routes>
    </MemoryRouter>
  );
}

afterEach(() => localStorage.clear());

describe('RoleRoute', () => {
  it('deixa passar papel permitido', () => {
    renderAs('CLUB');
    expect(screen.getByText('conteúdo restrito')).toBeInTheDocument();
  });

  it('redireciona papel não permitido', () => {
    renderAs('ATHLETE');
    expect(screen.getByText('lista')).toBeInTheDocument();
  });

  it('redireciona sessão sem papel', () => {
    renderAs(null);
    expect(screen.getByText('lista')).toBeInTheDocument();
  });
});

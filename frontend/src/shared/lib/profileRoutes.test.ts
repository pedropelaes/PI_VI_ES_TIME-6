import { describe, expect, it } from 'vitest';
import { getProfilePath, getStartConversationPath } from './profileRoutes';
import type { UserRole } from './userRole';

describe('getProfilePath', () => {
  it('aponta atleta para /athletes/:id', () => {
    expect(getProfilePath({ id: 'abc', role: 'ATHLETE' })).toBe('/athletes/abc');
  });

  it('aponta scout para /scouts/:id', () => {
    expect(getProfilePath({ id: 'abc', role: 'SCOUT' })).toBe('/scouts/abc');
  });

  it('aponta clube para /clubs/:id', () => {
    expect(getProfilePath({ id: 'abc', role: 'CLUB' })).toBe('/clubs/abc');
  });

  it('preserva o id como veio, sem reescrever', () => {
    const id = '3f2b1c4d-0000-4a1b-9c8d-7e6f5a4b3c2d';

    expect(getProfilePath({ id, role: 'SCOUT' })).toBe(`/scouts/${id}`);
  });

  it('falha alto em papel desconhecido, em vez de montar rota invalida', () => {
    const invalido = { id: 'abc', role: 'GHOST' as UserRole };

    expect(() => getProfilePath(invalido)).toThrow(/GHOST/);
  });
});

describe('getStartConversationPath', () => {
  it('aponta para a inbox com o destinatario em ?to=', () => {
    expect(getStartConversationPath('abc')).toBe('/messages?to=abc');
  });

  it('codifica o id para a querystring', () => {
    expect(getStartConversationPath('a b/c')).toBe('/messages?to=a%20b%2Fc');
  });
});

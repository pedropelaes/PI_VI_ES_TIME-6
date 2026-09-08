/**
 * Papel do usuario. MAIUSCULO em toda a stack (decisao Q7 da spec F2):
 * e o enum nativo do Postgres e o que `UserResponse` devolve. Traduzir caixa
 * entre camadas criaria um ponto de erro sem ganho nenhum.
 */
export type UserRole = 'ATHLETE' | 'SCOUT' | 'CLUB';

export const USER_ROLES: readonly UserRole[] = ['ATHLETE', 'SCOUT', 'CLUB'];

/** Rotulo em portugues para exibir na interface. */
export const USER_ROLE_LABELS: Record<UserRole, string> = {
  ATHLETE: 'Atleta',
  SCOUT: 'Scout',
  CLUB: 'Clube',
};

/**
 * Guarda de tipo para valores vindos de fora do TypeScript — o `user` gravado
 * no localStorage, por exemplo, pode ser de uma sessao antiga sem `role`.
 */
export function isUserRole(value: unknown): value is UserRole {
  return typeof value === 'string' && (USER_ROLES as readonly string[]).includes(value);
}

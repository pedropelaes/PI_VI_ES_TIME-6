import type { UserRole } from './userRole';

/**
 * Ponto unico de construcao de rota de perfil (decisao Q6 da spec F2).
 * Nenhum componente monta `/athletes/...`, `/scouts/...` ou `/clubs/...` na mao:
 * se a estrutura de rotas mudar, muda so aqui.
 */
const SEGMENT_BY_ROLE: Record<UserRole, string> = {
  ATHLETE: 'athletes',
  SCOUT: 'scouts',
  CLUB: 'clubs',
};

export function getProfilePath(user: { id: string; role: UserRole }): string {
  const segment = SEGMENT_BY_ROLE[user.role];

  if (!segment) {
    // Papel fora do enum so chega aqui vindo de dado externo (localStorage
    // antigo, resposta inesperada). Falhar alto e melhor do que navegar
    // para "/undefined/<id>".
    throw new Error(`Papel de usuario desconhecido: ${String(user.role)}`);
  }

  return `/${segment}/${user.id}`;
}

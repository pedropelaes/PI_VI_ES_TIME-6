import { Navigate, Outlet } from 'react-router-dom';
import { getUser } from '../../services/api';
import { isUserRole, type UserRole } from '../../shared/lib/userRole';

/**
 * Gate de UX por papel: evita a viagem perdida. Quem garante a regra é o backend.
 */
export function RoleRoute({ allow, redirectTo = '/opportunities' }: { allow: UserRole[]; redirectTo?: string }) {
  const role = getUser()?.role;
  return isUserRole(role) && allow.includes(role) ? <Outlet /> : <Navigate to={redirectTo} replace />;
}

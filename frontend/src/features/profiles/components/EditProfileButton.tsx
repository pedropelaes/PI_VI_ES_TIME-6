import { Link } from 'react-router-dom';
import { Pencil } from 'lucide-react';
import { getUser } from '../../../services/api';
import { PROFILE_EDIT_PATH } from '../../../shared/lib/profileRoutes';

interface Props {
  /** `userId` da rota; o perfil visitado. */
  userId: string | undefined;
}

/**
 * Atalho para a edicao, visivel so para o dono do perfil: compara o id da rota
 * com o da sessao gravada. Visitante nao ve o botao — e o backend recusaria o
 * PUT de qualquer forma, mas oferecer a acao seria mentir sobre o que da certo.
 */
export function EditProfileButton({ userId }: Props) {
  const storedUser = getUser();

  if (!userId || !storedUser || storedUser.id !== userId) {
    return null;
  }

  return (
    <Link className="btn-primary btn-link" to={PROFILE_EDIT_PATH}>
      <Pencil size={18} /> Editar perfil
    </Link>
  );
}

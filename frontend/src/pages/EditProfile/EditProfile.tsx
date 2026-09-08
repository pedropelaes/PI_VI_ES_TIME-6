import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { AthleteForm } from '../../features/profiles/components/AthleteForm';
import { AvatarUploader } from '../../features/profiles/components/AvatarUploader';
import { ClubForm } from '../../features/profiles/components/ClubForm';
import {
  ProfileFrame,
  ProfileStateScreen,
} from '../../features/profiles/components/ProfileShell';
import { ScoutForm } from '../../features/profiles/components/ScoutForm';
import {
  toAthleteFormValues,
  toClubFormValues,
  toScoutFormValues,
} from '../../features/profiles/editForm';
import { useMyAvatar } from '../../features/profiles/hooks/useMyAvatar';
import { useMyProfile } from '../../features/profiles/hooks/useMyProfile';
import { useUpdateMyProfile } from '../../features/profiles/hooks/useUpdateMyProfile';
import { resolveAvatarUrl } from '../../features/profiles/mappers';
import { getProfilePath } from '../../shared/lib/profileRoutes';
import './EditProfile.css';

/**
 * Edicao do proprio perfil (decisao E2: pagina propria, nao edicao inline).
 * O papel vem de `GET /profiles/me`, nao da URL, e decide qual formulario
 * aparece — os campos de cada papel sao disjuntos.
 */
export default function EditProfile() {
  const { data, isLoading, isError } = useMyProfile();
  const { save, isSaving, isSaved, errorMessage } = useUpdateMyProfile();
  const avatar = useMyAvatar();

  if (isLoading) {
    return <ProfileStateScreen message="Carregando perfil..." />;
  }

  if (isError || !data) {
    return (
      <ProfileStateScreen message="Não foi possível carregar o seu perfil. Tente novamente em instantes." />
    );
  }

  const me = data;
  const fullName = `${me.profile.first_name} ${me.profile.last_name}`.trim();

  // Salvar com erro nao pode parecer sucesso: as mensagens sao exclusivas e a
  // de falha so sai da tela quando um novo salvamento acontece.
  const status = (
    <>
      {isSaving && <p className="form-status">Salvando...</p>}
      {!isSaving && errorMessage && (
        <p className="form-status form-status-error" role="alert">
          Não foi possível salvar: {errorMessage}
        </p>
      )}
      {!isSaving && !errorMessage && isSaved && (
        <p className="form-status form-status-success" role="status">
          Perfil atualizado com sucesso.
        </p>
      )}
    </>
  );

  return (
    <ProfileFrame>
      <div className="edit-profile-card">
        <div className="edit-profile-header">
          <h1 className="profile-name">Editar perfil</h1>
          <Link
            className="btn-secondary btn-link"
            to={getProfilePath({ id: me.profile.user_id, role: me.role })}
          >
            <ArrowLeft size={18} /> Voltar ao perfil
          </Link>
        </div>

        <AvatarUploader
          avatarUrl={resolveAvatarUrl(me.profile.avatar_url)}
          initial={me.profile.first_name.charAt(0).toUpperCase()}
          fullName={fullName}
          onSelect={avatar.select}
          onRemove={avatar.remove}
          isBusy={avatar.isBusy}
          errorMessage={avatar.errorMessage}
        />

        {/*
          `initial` e sempre o perfil que o servidor confirmou: depois de salvar,
          a resposta entra no cache e vira a nova base de comparacao, entao um
          segundo "Salvar" sem edicao nao reenvia nada.
        */}
        {me.role === 'ATHLETE' && (
          <AthleteForm
            initial={toAthleteFormValues(me.profile)}
            onSave={save}
            isSaving={isSaving}
            status={status}
          />
        )}

        {me.role === 'SCOUT' && (
          <ScoutForm
            initial={toScoutFormValues(me.profile)}
            onSave={save}
            isSaving={isSaving}
            status={status}
          />
        )}

        {me.role === 'CLUB' && (
          <ClubForm
            initial={toClubFormValues(me.profile)}
            onSave={save}
            isSaving={isSaving}
            status={status}
          />
        )}
      </div>
    </ProfileFrame>
  );
}

import { useParams } from 'react-router-dom';
import { Shield } from 'lucide-react';
import { ClubDetails } from '../../features/profiles/components/ClubDetails';
import { EditProfileButton } from '../../features/profiles/components/EditProfileButton';
import {
  ProfileShell,
  ProfileStateScreen,
} from '../../features/profiles/components/ProfileShell';
import { useClubProfile } from '../../features/profiles/hooks/useClubProfile';

export default function ClubProfile() {
  const { userId } = useParams<{ userId: string }>();
  const { profile, isLoading, isError, notFound } = useClubProfile(userId);

  if (isLoading) {
    return <ProfileStateScreen message="Carregando perfil..." />;
  }

  // notFound antes de isError: um 404 tambem marca isError, e a mensagem
  // especifica ajuda mais do que a generica.
  if (notFound) {
    return <ProfileStateScreen message="Clube não encontrado." />;
  }

  if (isError || !profile) {
    return (
      <ProfileStateScreen message="Não foi possível carregar o perfil. Tente novamente em instantes." />
    );
  }

  return (
    <ProfileShell
      initial={profile.initial}
      avatarUrl={profile.avatarUrl}
      fullName={profile.fullName}
      location={profile.location}
      bio={profile.bio}
      actions={<EditProfileButton userId={userId} />}
      bioFallback="Este clube ainda não escreveu uma bio."
      badges={
        <span className="badge badge-primary">
          <Shield size={14} /> Clube
        </span>
      }
    >
      <ClubDetails profile={profile} />
    </ProfileShell>
  );
}

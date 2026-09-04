import { useParams } from 'react-router-dom';
import { Search } from 'lucide-react';
import {
  ProfileShell,
  ProfileStateScreen,
} from '../../features/profiles/components/ProfileShell';
import { ScoutDetails } from '../../features/profiles/components/ScoutDetails';
import { useScoutProfile } from '../../features/profiles/hooks/useScoutProfile';

export default function ScoutProfile() {
  const { userId } = useParams<{ userId: string }>();
  const { profile, isLoading, isError, notFound } = useScoutProfile(userId);

  if (isLoading) {
    return <ProfileStateScreen message="Carregando perfil..." />;
  }

  // notFound antes de isError: um 404 tambem marca isError, e a mensagem
  // especifica ajuda mais do que a generica.
  if (notFound) {
    return <ProfileStateScreen message="Scout não encontrado." />;
  }

  if (isError || !profile) {
    return (
      <ProfileStateScreen message="Não foi possível carregar o perfil. Tente novamente em instantes." />
    );
  }

  return (
    <ProfileShell
      initial={profile.initial}
      fullName={profile.fullName}
      location={profile.location}
      bio={profile.bio}
      bioFallback="Este scout ainda não escreveu uma bio."
      badges={
        <span className="badge badge-primary">
          <Search size={14} /> Scout
        </span>
      }
    >
      <ScoutDetails profile={profile} />
    </ProfileShell>
  );
}

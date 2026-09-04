import { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Activity,
  Bookmark,
  Check,
  Info,
  MessageCircle,
  Play,
  Shield,
} from 'lucide-react';
import { getUser } from '../../services/api';
import { AthleteStats } from '../../features/profiles/components/AthleteStats';
import { ClipsTab } from '../../features/profiles/components/ClipsTab';
import { ClubHistory } from '../../features/profiles/components/ClubHistory';
import { EditProfileButton } from '../../features/profiles/components/EditProfileButton';
import {
  ProfileShell,
  ProfileStateScreen,
} from '../../features/profiles/components/ProfileShell';
import { useAthleteClips } from '../../features/profiles/hooks/useAthleteClips';
import { useAthleteProfile } from '../../features/profiles/hooks/useAthleteProfile';

type Tab = 'clips' | 'analysis';

export default function PublicProfile() {
  const { userId } = useParams<{ userId: string }>();
  const { profile, isLoading, isError, notFound } = useAthleteProfile(userId);
  const { clips, isLoading: clipsLoading, isError: clipsError } = useAthleteClips(userId);
  const [activeTab, setActiveTab] = useState<Tab>('clips');

  // Mesma comparacao de `EditProfileButton`: o dono do perfil e quem tem esse
  // mesmo id na sessao gravada. "Seus clipes" so faz sentido para o dono — no
  // visitante (ex. um scout) o rotulo se referiria aos clipes do atleta como
  // se fossem do proprio visitante.
  const storedUser = getUser();
  const isOwner = Boolean(userId && storedUser && storedUser.id === userId);
  const clipsTabLabel = isOwner ? 'Seus clipes' : 'Clipes';

  if (isLoading) {
    return <ProfileStateScreen message="Carregando perfil..." />;
  }

  // notFound antes de isError: um 404 tambem marca isError, e a mensagem
  // especifica ajuda mais do que a generica.
  if (notFound) {
    return <ProfileStateScreen message="Atleta não encontrado." />;
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
      bioFallback="Este atleta ainda não escreveu uma bio."
      badges={
        <>
          <span className="badge badge-primary">
            <Shield size={14} /> {profile.positionLabel}
          </span>
          <span className="badge badge-success">
            <Activity size={14} /> {profile.statusLabel}
          </span>
          {profile.currentClub && (
            <span className="badge badge-neutral">
              <Info size={14} /> {profile.currentClub}
            </span>
          )}
        </>
      }
      actions={
        // Seguir/Salvar chegam na fatia 3 e Enviar Mensagem pertence ao M5.
        <>
          <EditProfileButton userId={userId} />
          <button className="btn-secondary" disabled title="Disponível em breve">
            <Check size={18} /> Seguir
          </button>
          <button className="btn-secondary" disabled title="Disponível em breve">
            <Bookmark size={18} /> Salvar Atleta
          </button>
          <button className="btn-primary" disabled title="Disponível em breve">
            <MessageCircle size={18} /> Enviar Mensagem
          </button>
        </>
      }
    >
      <AthleteStats profile={profile} />

      <ClubHistory history={profile.clubHistory} />

      <div className="tabs-nav">
        <button
          className={`tab-btn ${activeTab === 'clips' ? 'active' : ''}`}
          onClick={() => setActiveTab('clips')}
        >
          <Play size={18} className="tab-icon" />
          {clipsTabLabel}
        </button>
        <button
          className={`tab-btn ${activeTab === 'analysis' ? 'active' : ''}`}
          onClick={() => setActiveTab('analysis')}
        >
          <Activity size={18} className="tab-icon" />
          Análise Cinemática
        </button>
      </div>

      <div className="tabs-content">
        {activeTab === 'clips' && (
          <ClipsTab clips={clips} isLoading={clipsLoading} isError={clipsError} />
        )}

        {activeTab === 'analysis' && (
          <div className="placeholder-tab">
            <Activity size={48} />
            <h3>Graficos em Desenvolvimento</h3>
            <p>Os radares de desempenho ainda estao em desenvolvimento.</p>
          </div>
        )}
      </div>
    </ProfileShell>
  );
}

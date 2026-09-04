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
import { AthleteStats } from '../../features/profiles/components/AthleteStats';
import {
  ProfileShell,
  ProfileStateScreen,
} from '../../features/profiles/components/ProfileShell';
import { useAthleteProfile } from '../../features/profiles/hooks/useAthleteProfile';

type Tab = 'clips' | 'analysis';

export default function PublicProfile() {
  const { userId } = useParams<{ userId: string }>();
  const { profile, isLoading, isError, notFound } = useAthleteProfile(userId);
  const [activeTab, setActiveTab] = useState<Tab>('clips');

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

      <div className="tabs-nav">
        <button
          className={`tab-btn ${activeTab === 'clips' ? 'active' : ''}`}
          onClick={() => setActiveTab('clips')}
        >
          <Play size={18} className="tab-icon" />
          Videoteca
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
          <div className="placeholder-tab">
            <Play size={48} />
            <h3>Videoteca em Construcao</h3>
            <p>Os clipes deste atleta chegam na proxima fatia.</p>
          </div>
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

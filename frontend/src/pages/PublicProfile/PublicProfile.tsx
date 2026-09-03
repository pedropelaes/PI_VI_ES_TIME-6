import { useState } from 'react';
import type { ReactNode } from 'react';
import { useParams } from 'react-router-dom';
import { Activity, Info, Play } from 'lucide-react';
import { AboutTab } from '../../features/profiles/components/AboutTab';
import { ProfileHeader } from '../../features/profiles/components/ProfileHeader';
import { QuickStats } from '../../features/profiles/components/QuickStats';
import { useAthleteProfile } from '../../features/profiles/hooks/useAthleteProfile';
import './PublicProfile.css';

type Tab = 'clips' | 'analysis' | 'about';

/** Capa + container: comum a todos os estados, inclusive carregando e erro. */
function ProfileShell({ children }: { children: ReactNode }) {
  return (
    <div className="public-profile-root">
      <div className="profile-cover">
        <div className="profile-cover-pattern"></div>
      </div>

      <div className="public-profile-container">{children}</div>
    </div>
  );
}

export default function PublicProfile() {
  const { userId } = useParams<{ userId: string }>();
  const { profile, isLoading, isError, notFound } = useAthleteProfile(userId);
  const [activeTab, setActiveTab] = useState<Tab>('clips');

  if (isLoading) {
    return (
      <ProfileShell>
        <div className="profile-state">Carregando perfil...</div>
      </ProfileShell>
    );
  }

  // notFound antes de isError: um 404 tambem marca isError, e a mensagem
  // especifica ajuda mais do que a generica.
  if (notFound) {
    return (
      <ProfileShell>
        <div className="profile-state">Atleta nao encontrado.</div>
      </ProfileShell>
    );
  }

  if (isError || !profile) {
    return (
      <ProfileShell>
        <div className="profile-state">
          Nao foi possivel carregar o perfil. Tente novamente em instantes.
        </div>
      </ProfileShell>
    );
  }

  return (
    <ProfileShell>
      <ProfileHeader profile={profile} />

      <QuickStats profile={profile} />

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
          Analise Cinematica
        </button>
        <button
          className={`tab-btn ${activeTab === 'about' ? 'active' : ''}`}
          onClick={() => setActiveTab('about')}
        >
          <Info size={18} className="tab-icon" />
          Sobre
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

        {activeTab === 'about' && <AboutTab profile={profile} />}
      </div>
    </ProfileShell>
  );
}

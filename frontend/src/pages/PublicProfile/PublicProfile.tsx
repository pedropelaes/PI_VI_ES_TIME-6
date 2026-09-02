import React, { useState } from 'react';
import { 
  MapPin, 
  MessageCircle, 
  Bookmark, 
  Play, 
  Activity, 
  Info,
  Clock,
  Shield,
  Check
} from 'lucide-react';
import './PublicProfile.css';

// Mock
const mockAthlete = {
  first_name: "Jeh",
  last_name: "Rodrigues",
  position: "Atacante",
  location: "Campinas, SP",
  status: "Disponível para Clube",
  stats: {
    age: 19,
    foot: "Destro",
    height: "1.78m",
    clips: 42
  }
};

const mockClips = [
  { id: 1, title: "Picos de Velocidade vs Clube A", duration: "0:45", tags: ["Aceleração"] },
  { id: 2, title: "Passes Progressivos", duration: "1:12", tags: ["Visão de Jogo"] },
  { id: 3, title: "Recuperação de Posse", duration: "0:58", tags: ["Defesa"] },
];

export default function PublicProfile() {
  const [activeTab, setActiveTab] = useState<'clips' | 'analysis' | 'about'>('clips');

  const fullName = `${mockAthlete.first_name} ${mockAthlete.last_name}`;
  const initial = fullName.charAt(0);

  return (
    <div className="public-profile-root">
      
      {/* Capa com o Padrão Pontilhado */}
      <div className="profile-cover">
        <div className="profile-cover-pattern"></div>
      </div>

      <div className="public-profile-container">
        
        {/* Card Principal do Header */}
        <div className="profile-header-card">
          <div className="public-avatar">{initial}</div>
          
          <div className="profile-main-info">
            <div className="profile-badges">
              <span className="badge badge-primary">
                <Shield size={14} /> {mockAthlete.position}
              </span>
              <span className="badge badge-success">
                <Activity size={14} /> {mockAthlete.status}
              </span>
            </div>
            
            <h1 className="profile-name">{fullName}</h1>
            
            <div className="clip-meta" style={{ fontSize: '0.9rem', marginBottom: '1.5rem' }}>
              <MapPin size={16} /> {mockAthlete.location}
            </div>
          </div>

          <div className="profile-actions">
            <button className="btn-secondary">
              < Check size={18} /> Seguir
            </button>
            <button className="btn-secondary">
              <Bookmark size={18} /> Salvar Atleta
            </button>
            <button className="btn-primary">
              <MessageCircle size={18} /> Enviar Mensagem
            </button>
          </div>
        </div>

        {/* Estatísticas Rápidas */}
        <div className="quick-stats-grid">
          <div className="stat-box">
            <div className="stat-label">Idade</div>
            <div className="stat-value">{mockAthlete.stats.age}</div>
          </div>
          <div className="stat-box">
            <div className="stat-label">Pé Dominante</div>
            <div className="stat-value">{mockAthlete.stats.foot}</div>
          </div>
          <div className="stat-box">
            <div className="stat-label">Altura</div>
            <div className="stat-value">{mockAthlete.stats.height}</div>
          </div>
          <div className="stat-box">
            <div className="stat-label">Clipes Gerados IA</div>
            <div className="stat-value" style={{ color: '#5BADDA' }}>{mockAthlete.stats.clips}</div>
          </div>
        </div>

        {/* Navegação */}
        <div className="tabs-nav">
          <button 
            className={`tab-btn ${activeTab === 'clips' ? 'active' : ''}`}
            onClick={() => setActiveTab('clips')}
          >
            <Play size={18} style={{ display: 'inline', marginRight: '6px', marginBottom: '-4px' }}/>
            Videoteca
          </button>
          <button 
            className={`tab-btn ${activeTab === 'analysis' ? 'active' : ''}`}
            onClick={() => setActiveTab('analysis')}
          >
            <Activity size={18} style={{ display: 'inline', marginRight: '6px', marginBottom: '-4px' }}/>
            Análise Cinematica
          </button>
          <button 
            className={`tab-btn ${activeTab === 'about' ? 'active' : ''}`}
            onClick={() => setActiveTab('about')}
          >
            <Info size={18} style={{ display: 'inline', marginRight: '6px', marginBottom: '-4px' }}/>
            Sobre
          </button>
        </div>

        {/* Conteúdo das Abas */}
        <div className="tabs-content">
          
          {/* ABA: VIDEOTECA */}
          {activeTab === 'clips' && (
            <div className="clips-grid">
              {mockClips.map(clip => (
                <div key={clip.id} className="clip-card">
                  <div className="clip-thumbnail">
                    {/* Aqui entrará a tag <video> ou img de capa real depois */}
                    <div className="play-icon"><Play size={20} fill="currentColor"/></div>
                  </div>
                  <div className="clip-info">
                    <h3 className="clip-title">{clip.title}</h3>
                    <div className="clip-meta">
                      <Clock size={14} /> {clip.duration} • IA SmartScout
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ABA: ANÁLISE */}
          {activeTab === 'analysis' && (
            <div style={{ padding: '3rem 0', textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>
              <Activity size={48} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
              <h3 style={{ fontFamily: 'Outfit', color: '#fff', fontSize: '1.2rem' }}>Gráficos em Desenvolvimento</h3>
              <p>Aqui você integrará a biblioteca Recharts para mostrar os radares de desempenho.</p>
            </div>
          )}

          {/* ABA: SOBRE */}
          {activeTab === 'about' && (
            <div style={{ padding: '2rem 0', color: 'rgba(255,255,255,0.7)', lineHeight: '1.8' }}>
              <p>Atleta em desenvolvimento focado em transições ofensivas rápidas e passes de ruptura. 
                 Excelente leitura tática e capacidade de adaptação em diferentes esquemas táticos no meio-campo.</p>
              <h4 style={{ color: '#fff', marginTop: '2rem', fontFamily: 'Outfit' }}>Histórico</h4>
              <ul>
                <li>Base - Clube Local (2022-2024)</li>
                <li>Destaque - Campeonato Regional Sub-20</li>
              </ul>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
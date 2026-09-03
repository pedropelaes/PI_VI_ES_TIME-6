import { Activity, Bookmark, Check, MapPin, MessageCircle, Shield } from 'lucide-react';
import type { AthleteProfileView } from '../types';

interface Props {
  profile: AthleteProfileView;
}

/**
 * Cabecalho do perfil. Os botoes sociais ficam desabilitados nesta fatia:
 * Seguir/Salvar chegam na fatia 3 e Enviar Mensagem pertence ao M5.
 */
export function ProfileHeader({ profile }: Props) {
  return (
    <div className="profile-header-card">
      <div className="public-avatar">{profile.initial}</div>

      <div className="profile-main-info">
        <div className="profile-badges">
          <span className="badge badge-primary">
            <Shield size={14} /> {profile.positionLabel}
          </span>
          <span className="badge badge-success">
            <Activity size={14} /> {profile.statusLabel}
          </span>
        </div>

        <h1 className="profile-name">{profile.fullName}</h1>

        <div className="profile-location">
          <MapPin size={16} /> {profile.location}
        </div>
      </div>

      <div className="profile-actions">
        <button className="btn-secondary" disabled title="Disponivel em breve">
          <Check size={18} /> Seguir
        </button>
        <button className="btn-secondary" disabled title="Disponivel em breve">
          <Bookmark size={18} /> Salvar Atleta
        </button>
        <button className="btn-primary" disabled title="Disponivel em breve">
          <MessageCircle size={18} /> Enviar Mensagem
        </button>
      </div>
    </div>
  );
}

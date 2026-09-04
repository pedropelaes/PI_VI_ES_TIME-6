import type { ReactNode } from 'react';
import { MapPin } from 'lucide-react';
import './profiles.css';

/**
 * Capa + container. Comum a todos os estados da pagina, inclusive carregando e
 * erro, quando ainda nao ha perfil para desenhar o cabecalho.
 */
export function ProfileFrame({ children }: { children: ReactNode }) {
  return (
    <div className="public-profile-root">
      <div className="profile-cover">
        <div className="profile-cover-pattern"></div>
      </div>

      <div className="public-profile-container">{children}</div>
    </div>
  );
}

/** Tela de estado (carregando, nao encontrado, erro) dentro da mesma moldura. */
export function ProfileStateScreen({ message }: { message: string }) {
  return (
    <ProfileFrame>
      <div className="profile-state">{message}</div>
    </ProfileFrame>
  );
}

interface ProfileShellProps {
  /** Inicial exibida no avatar enquanto nao ha upload de imagem (fora de escopo). */
  initial: string;
  fullName: string;
  location: string;
  bio: string | null;
  /** Texto exibido quando o usuario ainda nao escreveu bio. */
  bioFallback: string;
  /** Selos do papel: posicao e status do atleta, "Scout", "Clube"... */
  badges?: ReactNode;
  /** Acoes sociais; hoje so o atleta tem (todas desabilitadas ate a fatia 3). */
  actions?: ReactNode;
  /** Blocos especificos do papel: AthleteStats, ScoutDetails, ClubDetails. */
  children?: ReactNode;
}

/**
 * Decisao Q8: cabecalho, avatar, nome, selos, localizacao e bio sao identicos
 * nos tres perfis e moram aqui. Sem isso, cada ajuste visual viraria tres
 * edicoes — que e exatamente o custo que tres paginas separadas cobram.
 */
export function ProfileShell({
  initial,
  fullName,
  location,
  bio,
  bioFallback,
  badges,
  actions,
  children,
}: ProfileShellProps) {
  return (
    <ProfileFrame>
      <div className="profile-header-card">
        <div className="public-avatar">{initial}</div>

        <div className="profile-main-info">
          {badges && <div className="profile-badges">{badges}</div>}

          <h1 className="profile-name">{fullName}</h1>

          <div className="profile-location">
            <MapPin size={16} /> {location}
          </div>
        </div>

        {actions && <div className="profile-actions">{actions}</div>}
      </div>

      <section className="profile-bio">
        <h2>Sobre</h2>
        <p>{bio ?? bioFallback}</p>
      </section>

      {children}
    </ProfileFrame>
  );
}

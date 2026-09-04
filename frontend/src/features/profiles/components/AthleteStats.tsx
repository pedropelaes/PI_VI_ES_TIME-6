import type { AthleteProfileView } from '../types';

interface Props {
  profile: AthleteProfileView;
}

/** Numeros do atleta. Todos os valores ja chegam formatados do mapper. */
export function AthleteStats({ profile }: Props) {
  return (
    <div className="quick-stats-grid">
      <div className="stat-box">
        <div className="stat-label">Idade</div>
        <div className="stat-value">{profile.ageLabel}</div>
      </div>
      <div className="stat-box">
        <div className="stat-label">Pé Dominante</div>
        <div className="stat-value">{profile.footLabel}</div>
      </div>
      <div className="stat-box">
        <div className="stat-label">Altura</div>
        <div className="stat-value">{profile.heightLabel}</div>
      </div>
      <div className="stat-box">
        <div className="stat-label">Clipes Gerados IA</div>
        <div className="stat-value stat-value-highlight">{profile.clipsCount}</div>
      </div>
    </div>
  );
}

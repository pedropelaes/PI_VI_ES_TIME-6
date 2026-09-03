import type { AthleteProfileView } from '../types';

interface Props {
  profile: AthleteProfileView;
}

/**
 * Aba "Sobre". Mostra apenas o que o atleta de fato preencheu: a antiga lista
 * de "Historico" era texto inventado, sem nenhum campo de dominio por tras.
 */
export function AboutTab({ profile }: Props) {
  return (
    <div className="about-tab">
      <p>{profile.bio ?? 'Este atleta ainda nao escreveu uma bio.'}</p>

      {profile.currentClub && <p className="about-club">Clube atual: {profile.currentClub}</p>}
    </div>
  );
}

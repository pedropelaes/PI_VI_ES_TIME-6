export type Position =
  | 'GOLEIRO'
  | 'ZAGUEIRO'
  | 'LATERAL'
  | 'VOLANTE'
  | 'MEIA'
  | 'ATACANTE';

export type DominantFoot = 'DESTRO' | 'CANHOTO' | 'AMBIDESTRO';

export type AthleteStatus = 'DISPONIVEL' | 'CONTRATADO' | 'NAO_DISPONIVEL';

/** Resposta crua da API, em snake_case. */
export interface AthleteProfileDTO {
  user_id: string;
  first_name: string;
  last_name: string;
  position: Position | null;
  status: AthleteStatus;
  age: number | null;
  height_cm: number | null;
  dominant_foot: DominantFoot | null;
  city: string | null;
  state: string | null;
  current_club: string | null;
  bio: string | null;
  avatar_url: string | null;
  clips_count: number;
}

/** O que a tela consome: tudo ja formatado, sem logica no JSX. */
export interface AthleteProfileView {
  userId: string;
  fullName: string;
  initial: string;
  positionLabel: string;
  statusLabel: string;
  location: string;
  ageLabel: string;
  heightLabel: string;
  footLabel: string;
  currentClub: string | null;
  bio: string | null;
  avatarUrl: string | null;
  clipsCount: number;
}

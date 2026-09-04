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
  /** Texto livre multilinha (decisao E1 da spec de edicao de perfil). */
  club_history: string | null;
  bio: string | null;
  avatar_url: string | null;
  clips_count: number;
  /**
   * Opcional de proposito: a resposta publica expoe `age` derivada, nao a data.
   * O formulario de edicao escreve `birth_date` no PUT, entao o campo comeca
   * vazio quando a API nao o devolve — e so vai no payload se o usuario mexer.
   */
  birth_date?: string | null;
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
  /** Texto livre multilinha; a tela preserva as quebras de linha ao exibir. */
  clubHistory: string | null;
  bio: string | null;
  avatarUrl: string | null;
  clipsCount: number;
}

export type ClubCategory = 'SUB_15' | 'SUB_17' | 'SUB_20' | 'PROFISSIONAL';

/** Resposta crua de GET /profiles/scouts/{id}. */
export interface ScoutProfileDTO {
  user_id: string;
  first_name: string;
  last_name: string;
  organization: string | null;
  credential: string | null;
  city: string | null;
  state: string | null;
  bio: string | null;
  avatar_url: string | null;
}

export interface ScoutProfileView {
  userId: string;
  fullName: string;
  initial: string;
  organizationLabel: string;
  credentialLabel: string;
  location: string;
  bio: string | null;
  avatarUrl: string | null;
}

/** Resposta crua de GET /profiles/clubs/{id}. */
export interface ClubProfileDTO {
  user_id: string;
  first_name: string;
  last_name: string;
  legal_name: string | null;
  cnpj: string | null;
  categories: string[];
  city: string | null;
  state: string | null;
  bio: string | null;
  avatar_url: string | null;
}

export interface ClubProfileView {
  userId: string;
  fullName: string;
  initial: string;
  legalNameLabel: string;
  cnpjLabel: string;
  categoryLabels: string[];
  location: string;
  bio: string | null;
  avatarUrl: string | null;
}

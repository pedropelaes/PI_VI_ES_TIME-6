import type { AthleteStatus, Position } from '../profiles/types';

/** Respostas cruas da API (snake_case), espelhando backend/app/modules/feed/schemas.py. */
export interface FeedAthleteDTO {
  user_id: string;
  first_name: string;
  last_name: string;
  avatar_url: string | null;
  position: Position | null;
  age: number | null;
  city: string | null;
  state: string | null;
  status: AthleteStatus;
}

export interface FeedItemDTO {
  id: string;
  file_url: string;
  duration_seconds: number;
  published_at: string;
  like_count: number;
  liked_by_me: boolean;
  athlete: FeedAthleteDTO;
}

export interface FeedPageDTO {
  items: FeedItemDTO[];
  next_cursor: string | null;
}

export interface LikeStateDTO {
  clip_id: string;
  like_count: number;
  liked_by_me: boolean;
}

/** Filtros aceitos por GET /feed. Todos opcionais; ausente = sem filtro. */
export interface FeedFilters {
  position?: Position;
  status?: AthleteStatus;
  maxAge?: number;
  q?: string;
}

/** O que o card consome: tudo já formatado, sem lógica no JSX. */
export interface FeedItemView {
  id: string;
  videoUrl: string;
  /** Caminho relativo da API, usado pelo download autenticado. */
  fileUrl: string;
  durationLabel: string;
  publishedLabel: string;
  likeCount: number;
  likedByMe: boolean;
  athlete: {
    userId: string;
    fullName: string;
    initial: string;
    avatarUrl: string | null;
    /** Ex.: "Atacante · 19 anos · Campinas/SP" — só com o que estiver preenchido. */
    details: string;
    isAvailable: boolean;
    profilePath: string;
  };
}
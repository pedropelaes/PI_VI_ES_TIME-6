import { API_BASE } from '../../shared/lib/httpClient';
import { getProfilePath } from '../../shared/lib/profileRoutes';
import { POSITION_LABELS, resolveAvatarUrl } from '../profiles/mappers';
import type { FeedFilters, FeedItemDTO, FeedItemView } from './types';

export function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  const min = Math.floor(total / 60);
  const sec = total % 60;
  return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

/**
 * A API devolve datetime com fuso ("...+00:00"), entao new Date() ja interpreta certo.
 * Se o Safari mostrar "recentemente", corte os microssegundos do valor antes de parsear.
 */
export function formatRelativeTime(value: string, now: number = Date.now()): string {
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return 'recentemente';

  const minutes = Math.max(0, Math.floor((now - timestamp) / 60000));
  if (minutes < 1) return 'agora';
  if (minutes < 60) return `há ${minutes} min`;
  if (minutes < 1440) return `há ${Math.floor(minutes / 60)} h`;
  return `há ${Math.floor(minutes / 1440)} d`;
}

export function toFeedItemView(dto: FeedItemDTO, now: number = Date.now()): FeedItemView {
  const { athlete } = dto;
  const fullName = `${athlete.first_name} ${athlete.last_name}`.trim();
  const local = athlete.city && athlete.state ? `${athlete.city}/${athlete.state}` : athlete.city ?? athlete.state;

  const details = [
    athlete.position ? POSITION_LABELS[athlete.position] : null,
    athlete.age != null ? `${athlete.age} anos` : null,
    local,
  ]
    .filter(Boolean)
    .join(' · ');

  return {
    id: dto.id,
    videoUrl: `${API_BASE}${dto.file_url}`,
    fileUrl: dto.file_url,
    durationLabel: formatDuration(dto.duration_seconds),
    publishedAt: dto.published_at,
    likeCount: dto.like_count,
    likedByMe: dto.liked_by_me,
    athlete: {
      userId: athlete.user_id,
      fullName,
      initial: fullName.charAt(0).toUpperCase() || '?',
      avatarUrl: resolveAvatarUrl(athlete.avatar_url),
      details: details || 'Atleta',
      isAvailable: athlete.status === 'DISPONIVEL',
      profilePath: getProfilePath({ id: athlete.user_id, role: 'ATHLETE' }),
    },
  };
}

/** Monta a query string de GET /feed. Campos vazios não vão na URL. */
export function buildFeedQuery(filters: FeedFilters, cursor?: string | null, limit = 12): string {
  const params = new URLSearchParams();
  if (filters.position) params.set('position', filters.position);
  if (filters.status) params.set('status', filters.status);
  if (filters.maxAge != null) params.set('max_age', String(filters.maxAge));
  const q = filters.q?.trim();
  if (q) params.set('q', q);
  if (cursor) params.set('cursor', cursor);
  params.set('limit', String(limit));
  return params.toString();
}
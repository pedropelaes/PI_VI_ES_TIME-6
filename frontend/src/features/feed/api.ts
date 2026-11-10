import { httpDelete, httpGet, httpPost } from '../../shared/lib/httpClient';
import { buildFeedQuery } from './mappers';
import type { FeedFilters, FeedPageDTO, LikeStateDTO } from './types';

/** Uma página do feed. `cursor` vem do `next_cursor` da página anterior. */
export function getFeed(filters: FeedFilters, cursor?: string | null): Promise<FeedPageDTO> {
  return httpGet<FeedPageDTO>(`/feed?${buildFeedQuery(filters, cursor)}`);
}

export function likeClip(clipId: string): Promise<LikeStateDTO> {
  return httpPost<LikeStateDTO>(`/feed/clips/${clipId}/like`);
}

export function unlikeClip(clipId: string): Promise<LikeStateDTO> {
  return httpDelete<LikeStateDTO>(`/feed/clips/${clipId}/like`);
}
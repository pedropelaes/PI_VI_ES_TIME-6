import { useMutation, useQueryClient, type InfiniteData } from '@tanstack/react-query';
import { likeClip, unlikeClip } from '../api';
import type { FeedPageDTO, LikeStateDTO } from '../types';
import { FEED_QUERY_KEY } from './useFeed';

type FeedCache = InfiniteData<FeedPageDTO, string | null>;

/** Aplica o novo estado de curtida ao clipe em todas as páginas/filtros em cache. */
function patchClip(cache: FeedCache | undefined, clipId: string, likedByMe: boolean, likeCount?: number) {
  if (!cache) return cache;
  return {
    ...cache,
    pages: cache.pages.map((page) => ({
      ...page,
      items: page.items.map((item) => {
        if (item.id !== clipId) return item;
        const delta = likedByMe === item.liked_by_me ? 0 : likedByMe ? 1 : -1;
        return {
          ...item,
          liked_by_me: likedByMe,
          like_count: likeCount ?? Math.max(0, item.like_count + delta),
        };
      }),
    })),
  };
}

export function useToggleLike() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ clipId, like }: { clipId: string; like: boolean }): Promise<LikeStateDTO> =>
      like ? likeClip(clipId) : unlikeClip(clipId),

    onMutate: async ({ clipId, like }) => {
      await queryClient.cancelQueries({ queryKey: FEED_QUERY_KEY });
      const anterior = queryClient.getQueriesData<FeedCache>({ queryKey: FEED_QUERY_KEY });
      queryClient.setQueriesData<FeedCache>({ queryKey: FEED_QUERY_KEY }, (cache) =>
        patchClip(cache, clipId, like)
      );
      return { anterior };
    },

    onError: (_erro, _vars, contexto) => {
      contexto?.anterior.forEach(([key, data]) => queryClient.setQueryData(key, data));
    },

    onSuccess: (estado) => {
      queryClient.setQueriesData<FeedCache>({ queryKey: FEED_QUERY_KEY }, (cache) =>
        patchClip(cache, estado.clip_id, estado.liked_by_me, estado.like_count)
      );
    },
  });
}
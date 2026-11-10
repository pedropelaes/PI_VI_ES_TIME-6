import { useInfiniteQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { getFeed } from '../api';
import { toFeedItemView } from '../mappers';
import type { FeedFilters, FeedItemView } from '../types';

export const FEED_QUERY_KEY = ['feed'] as const;

interface UseFeedResult {
  items: FeedItemView[];
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  refetch: () => void;
}

/**
 * Feed paginado por cursor. Cada combinação de filtros tem seu próprio cache
 * (o filtro faz parte da chave), então voltar para "Todos" é instantâneo.
 */
export function useFeed(filters: FeedFilters): UseFeedResult {
  const query = useInfiniteQuery({
    queryKey: [...FEED_QUERY_KEY, filters],
    queryFn: ({ pageParam }) => getFeed(filters, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  });

  const items = useMemo(
    () => (query.data?.pages ?? []).flatMap((page) => page.items.map((item) => toFeedItemView(item))),
    [query.data]
  );

  return {
    items,
    isLoading: query.isPending,
    isError: query.isError,
    error: query.error,
    hasNextPage: query.hasNextPage,
    isFetchingNextPage: query.isFetchingNextPage,
    fetchNextPage: () => void query.fetchNextPage(),
    refetch: () => void query.refetch(),
  };
}
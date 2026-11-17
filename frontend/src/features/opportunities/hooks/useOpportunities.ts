import { useInfiniteQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { getOpportunities } from '../api';
import type { OpportunityFilters } from '../types';
import { OPPORTUNITIES_KEY } from './queries';

/** Peneiras abertas paginadas por cursor; cada combinação de filtros tem seu cache. */
export function useOpportunities(filters: OpportunityFilters) {
  const query = useInfiniteQuery({
    queryKey: [...OPPORTUNITIES_KEY, 'list', filters],
    queryFn: ({ pageParam }) => getOpportunities(filters, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  });

  const items = useMemo(() => (query.data?.pages ?? []).flatMap((p) => p.items), [query.data]);

  return {
    items,
    isLoading: query.isPending,
    isError: query.isError,
    hasNextPage: query.hasNextPage,
    isFetchingNextPage: query.isFetchingNextPage,
    fetchNextPage: () => void query.fetchNextPage(),
  };
}

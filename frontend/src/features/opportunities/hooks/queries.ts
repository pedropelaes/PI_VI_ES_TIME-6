import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getApplicants, getMyApplications, getMyOpportunities, getOpportunity } from '../api';

export const OPPORTUNITIES_KEY = ['opportunities'] as const;

export function useOpportunity(id: string) {
  return useQuery({ queryKey: [...OPPORTUNITIES_KEY, 'detail', id], queryFn: () => getOpportunity(id) });
}

export function useApplicants(id: string, enabled: boolean) {
  return useQuery({
    queryKey: [...OPPORTUNITIES_KEY, 'applicants', id],
    queryFn: () => getApplicants(id),
    enabled,
  });
}

export function useMyOpportunities() {
  return useQuery({ queryKey: [...OPPORTUNITIES_KEY, 'mine'], queryFn: getMyOpportunities });
}

export function useMyApplications() {
  return useQuery({ queryKey: [...OPPORTUNITIES_KEY, 'my-applications'], queryFn: getMyApplications });
}

/**
 * Toda mutação de oportunidade invalida tudo debaixo de ['opportunities']: as listas
 * são pequenas e isso evita cache velho (vaga, status, cancelada) sem regra por tela.
 */
export function useOpportunityMutation<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: OPPORTUNITIES_KEY }),
  });
}

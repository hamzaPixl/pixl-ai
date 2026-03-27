/**
 * Budget query hooks.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { budget } from '@/lib/api';
import { queryKeys } from '@/lib/query-keys';
import { toast } from 'sonner';

export function useBudget(projectId?: string) {
  return useQuery({
    queryKey: queryKeys.budget.config(projectId!),
    queryFn: () => budget.get(),
    enabled: !!projectId,
  });
}

export function useCosts(projectId?: string, sessionId?: string) {
  return useQuery({
    queryKey: queryKeys.budget.costs(projectId!, sessionId),
    queryFn: () => budget.getCosts(sessionId),
    enabled: !!projectId,
  });
}

export function useUpdateBudget(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (monthlyUsd: number) => budget.update(monthlyUsd),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.budget.all(projectId) });
      toast.success('Budget updated');
    },
    onError: () => toast.error('Failed to update budget'),
  });
}

export function useUnpauseBudget(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => budget.unpause(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.budget.all(projectId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions.all(projectId) });
      toast.success(`Unpaused ${data.count} session(s)`);
    },
    onError: () => toast.error('Failed to unpause sessions'),
  });
}

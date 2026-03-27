/**
 * Dashboard / Factory Home query hooks.
 *
 * These hooks now accept projectId as a parameter.
 * Components should pass projectId from route params.
 */

import { useQuery } from "@tanstack/react-query";
import { dashboard } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

export function useDashboardSummary(projectId: string) {
  return useQuery({
    queryKey: queryKeys.dashboard.summary(projectId),
    queryFn: () => dashboard.summary(),
    enabled: !!projectId,
    refetchInterval: 30000, // Refetch every 30 seconds
  });
}

export function useDashboardProgress(projectId: string) {
  return useQuery({
    queryKey: queryKeys.dashboard.progress(projectId),
    queryFn: () => dashboard.progress(),
    enabled: !!projectId,
    refetchInterval: 30000,
  });
}

export function useFactoryHome(projectId: string) {
  const result = useQuery({
    queryKey: queryKeys.dashboard.overview(projectId),
    queryFn: () => dashboard.overview(),
    enabled: !!projectId,
    refetchInterval: 30000,
  });

  return {
    data: result.data,
    isLoading: result.isLoading,
    error: result.error,
    refetch: result.refetch,
  };
}

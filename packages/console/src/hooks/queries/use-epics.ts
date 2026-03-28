/**
 * Epic query hooks.
 *
 * These hooks now accept projectId as a parameter.
 * Components should pass projectId from route params.
 */

import { useQuery } from "@tanstack/react-query";
import { epics } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

export function useEpics(params?: { limit?: number; offset?: number; status?: string }, projectId?: string) {
  return useQuery({
    queryKey: queryKeys.epics.list(projectId!, params),
    queryFn: async () => {
      const res = await epics.list(params);
      // Backend returns PaginatedResponse { items, total, page, size }
      return Array.isArray(res) ? res : (res as any).items ?? [];
    },
    enabled: !!projectId,
  });
}

export function useEpic(id: string, projectId?: string) {
  return useQuery({
    queryKey: queryKeys.epics.detail(projectId!, id),
    queryFn: () => epics.get(id),
    enabled: !!projectId && !!id,
  });
}

export function useEpicFeatures(id: string, projectId?: string) {
  return useQuery({
    queryKey: queryKeys.epics.features(projectId!, id),
    queryFn: () => epics.features.list(id),
    enabled: !!projectId && !!id,
  });
}

export function useEpicHistory(id: string, projectId?: string) {
  return useQuery({
    queryKey: queryKeys.epics.history(projectId!, id),
    queryFn: () => epics.history(id),
    enabled: !!projectId && !!id,
  });
}


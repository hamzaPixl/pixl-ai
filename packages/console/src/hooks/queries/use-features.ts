/**
 * Feature query hooks.
 *
 * These hooks now accept projectId as a parameter.
 * Components should pass projectId from route params.
 */

import { useQuery } from "@tanstack/react-query";
import { features } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

export function useFeatures(params?: {
  limit?: number;
  offset?: number;
  status?: string;
  epic_id?: string;
  roadmap_id?: string;
}, projectId?: string) {
  return useQuery({
    queryKey: queryKeys.features.list(projectId!, params),
    queryFn: () => features.list(params),
    enabled: !!projectId,
  });
}

export function useFeature(id: string, projectId?: string) {
  return useQuery({
    queryKey: queryKeys.features.detail(projectId!, id),
    queryFn: () => features.get(id),
    enabled: !!projectId && !!id,
  });
}

export function useFeatureHistory(id: string, projectId?: string) {
  return useQuery({
    queryKey: queryKeys.features.history(projectId!, id),
    queryFn: () => features.history(id),
    enabled: !!projectId && !!id,
  });
}


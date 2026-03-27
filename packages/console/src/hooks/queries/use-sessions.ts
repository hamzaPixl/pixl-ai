/**
 * Session query hooks.
 *
 * These hooks now accept projectId as an optional parameter.
 * If not provided, they'll attempt to get it from the route params.
 * Components should pass projectId from useParams for better type safety.
 */

import { useQuery } from "@tanstack/react-query";
import { sessions } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { SessionListEntry, WorkflowSession } from "@/types/api";

export interface SessionsListParams extends Record<string, string | number | boolean | undefined> {
  limit?: number;
  offset?: number;
  status?: "running" | "completed" | "failed" | "paused" | "stalled";
  feature_id?: string;
}

/**
 * Hook for fetching sessions list.
 * Call with projectId from route params: const { projectId } = useParams({ from: '/project/$projectId' });
 */
export function useSessions(params?: SessionsListParams, projectId?: string) {
  // TODO: In future, we can use useRouteContext to get projectId automatically
  // For now, rely on components passing projectId or using the store fallback
  return useQuery({
    queryKey: queryKeys.sessions.list(projectId!, params),
    queryFn: async (): Promise<SessionListEntry[]> => {
      const res = await sessions.list(params);
      // Backend returns PaginatedResponse { items, total, page, size }
      return Array.isArray(res) ? res : (res as any).items ?? [];
    },
    enabled: !!projectId,
    refetchInterval: (query) => {
      // Refetch more frequently if any session is running
      const data = query.state.data;
      const hasActive = data?.some(s => s.status === "running" || s.status === "stalled");
      return hasActive ? 5000 : false;
    },
  });
}

export function useSession(id: string, projectId?: string) {
  return useQuery({
    queryKey: queryKeys.sessions.detail(projectId!, id),
    queryFn: () => sessions.get(id),
    enabled: !!projectId && !!id,
    refetchInterval: (query) => {
      // Refetch more frequently if session is running
      const data = query.state.data as WorkflowSession | undefined;
      return data?.status === "running" || data?.status === "stalled" ? 5000 : false;
    },
  });
}

export function useSessionNodes(sessionId: string, projectId?: string) {
  return useQuery({
    queryKey: queryKeys.sessions.nodes(projectId!, sessionId),
    queryFn: () => sessions.nodes(sessionId),
    enabled: !!projectId && !!sessionId,
  });
}


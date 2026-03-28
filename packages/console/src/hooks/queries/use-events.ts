/**
 * Event query hooks.
 */

import { useQuery } from "@tanstack/react-query";
import { events } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useProjectStore, selectCurrentProjectId } from "@/stores/project";

export function useEvents(params?: {
  limit?: number;
  offset?: number;
  session_id?: string;
}, isLive?: boolean) {
  const projectId = useProjectStore(selectCurrentProjectId);

  return useQuery({
    queryKey: queryKeys.events.list(projectId!, params),
    queryFn: () => events.list(params),
    enabled: !!projectId,
    refetchInterval: isLive ? 15000 : false,
  });
}

export function useEventCounts(params?: { session_id?: string }) {
  const projectId = useProjectStore(selectCurrentProjectId);

  return useQuery({
    queryKey: queryKeys.events.counts(projectId!, params),
    queryFn: () => events.counts(params),
    enabled: !!projectId,
  });
}

export function useEventTransitions(sessionId?: string) {
  const projectId = useProjectStore(selectCurrentProjectId);

  return useQuery({
    queryKey: queryKeys.events.transitions(projectId!, sessionId),
    queryFn: () => events.transitions(sessionId),
    enabled: !!projectId,
  });
}

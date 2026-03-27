/**
 * Heartbeat run query hooks.
 */

import { useQuery } from "@tanstack/react-query";
import { heartbeatRuns } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

export function useHeartbeatRuns(sessionId: string, projectId?: string) {
  return useQuery({
    queryKey: queryKeys.heartbeatRuns.list(projectId!, sessionId),
    queryFn: () => heartbeatRuns.list(sessionId),
    enabled: !!projectId && !!sessionId,
  });
}

export function useActiveRun(sessionId: string, projectId?: string) {
  return useQuery({
    queryKey: queryKeys.heartbeatRuns.active(projectId!, sessionId),
    queryFn: () => heartbeatRuns.getActive(sessionId),
    enabled: !!projectId && !!sessionId,
    refetchInterval: 5000,
  });
}

export function useStalledRuns(projectId?: string) {
  return useQuery({
    queryKey: queryKeys.heartbeatRuns.stalled(projectId!),
    queryFn: () => heartbeatRuns.getStalled(),
    enabled: !!projectId,
    refetchInterval: 15000,
  });
}

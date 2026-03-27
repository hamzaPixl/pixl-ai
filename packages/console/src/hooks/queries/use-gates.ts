/**
 * Gate query and mutation hooks.
 *
 * These hooks now accept projectId as a parameter.
 * Components should pass projectId from route params.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { gates, views } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { GateApproveRequest, GateRejectRequest } from "@/types/api";

export function useGates(sessionId: string, projectId?: string, isLive?: boolean) {
  return useQuery({
    queryKey: queryKeys.gates.list(projectId!, sessionId),
    queryFn: () => gates.list(sessionId),
    enabled: !!projectId && !!sessionId,
    refetchInterval: isLive ? 10000 : false,
  });
}

export function useGateInbox(projectId?: string) {
  return useQuery({
    queryKey: queryKeys.views.gateInbox(projectId!),
    queryFn: () => views.gateInbox(),
    enabled: !!projectId,
    refetchInterval: 10000,
  });
}

// Mutations

export function useApproveGate(projectId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, gateId, data }: {
      sessionId: string;
      gateId: string;
      data?: GateApproveRequest;
    }) => gates.approve(sessionId, gateId, data),
    onSuccess: (_, { sessionId }) => {
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.gates.list(projectId, sessionId) });
        queryClient.invalidateQueries({ queryKey: queryKeys.gates.all(projectId) });
        queryClient.invalidateQueries({ queryKey: queryKeys.sessions.detail(projectId, sessionId) });
        queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.all(projectId) });
      }
    },
  });
}

export function useRejectGate(projectId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, gateId, data }: {
      sessionId: string;
      gateId: string;
      data?: GateRejectRequest;
    }) => gates.reject(sessionId, gateId, data),
    onSuccess: (_, { sessionId }) => {
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.gates.list(projectId, sessionId) });
        queryClient.invalidateQueries({ queryKey: queryKeys.gates.all(projectId) });
        queryClient.invalidateQueries({ queryKey: queryKeys.sessions.detail(projectId, sessionId) });
        queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.all(projectId) });
      }
    },
  });
}

/**
 * Agent query hooks.
 *
 * These hooks now accept projectId as a parameter.
 * Components should pass projectId from route params.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { agents } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

export function useAgents(projectId?: string) {
  return useQuery({
    queryKey: queryKeys.agents.list(projectId!),
    queryFn: () => agents.list(),
    enabled: !!projectId,
  });
}

export function useAllowedModels(projectId?: string) {
  return useQuery({
    queryKey: queryKeys.agents.models(projectId!),
    queryFn: () => agents.allowedModels(),
    enabled: !!projectId,
  });
}

export function useClassificationModel(projectId?: string) {
  return useQuery({
    queryKey: queryKeys.agents.classificationModel(projectId!),
    queryFn: () => agents.classificationModel(),
    enabled: !!projectId,
  });
}

export function useSessionReportModel(projectId?: string) {
  return useQuery({
    queryKey: queryKeys.agents.sessionReportModel(projectId!),
    queryFn: () => agents.sessionReportModel(),
    enabled: !!projectId,
  });
}

export function useUpdateAgentModel(projectId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ agentName, model }: { agentName: string; model: string | null }) =>
      agents.updateModel(agentName, { model }),
    onSuccess: () => {
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.agents.all(projectId) });
      }
    },
  });
}

export function useUpdateClassificationModel(projectId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ model }: { model: string | null }) =>
      agents.updateClassificationModel({ model }),
    onSuccess: () => {
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.agents.all(projectId) });
      }
    },
  });
}

export function useUpdateSessionReportModel(projectId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ model }: { model: string | null }) =>
      agents.updateSessionReportModel({ model }),
    onSuccess: () => {
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.agents.all(projectId) });
      }
    },
  });
}

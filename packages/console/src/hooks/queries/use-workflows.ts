/**
 * Workflow query hooks.
 */

import { useQuery } from "@tanstack/react-query";
import { workflows } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

export function useWorkflows(projectId?: string) {
  return useQuery({
    queryKey: queryKeys.workflows.list(projectId!),
    queryFn: () => workflows.list(),
    enabled: !!projectId,
  });
}

export function useWorkflowDetail(projectId?: string, workflowId?: string) {
  return useQuery({
    queryKey: queryKeys.workflows.detail(projectId!, workflowId!),
    queryFn: () => workflows.detail(workflowId!),
    enabled: !!projectId && !!workflowId,
  });
}

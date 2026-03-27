import { useMutation, type QueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

export function useSessionMutations(
  sessionId: string,
  projectId: string,
  queryClient: QueryClient,
) {
  const invalidateSession = () => {
    if (projectId) {
      queryClient.invalidateQueries({
        queryKey: queryKeys.sessions.detail(projectId, sessionId),
      });
    }
  };

  const pauseMutation = useMutation({
    mutationFn: () => api.control.pause(sessionId),
    onSuccess: invalidateSession,
  });

  const resumeMutation = useMutation({
    mutationFn: () => api.control.resume(sessionId),
    onSuccess: invalidateSession,
  });

  const forceResumeMutation = useMutation({
    mutationFn: () => api.control.forceResume(sessionId),
    onSuccess: invalidateSession,
  });

  const draftReportMutation = useMutation({
    mutationFn: () => api.sessions.draftReport(sessionId, "ui"),
    onSuccess: () => {
      if (projectId) {
        queryClient.invalidateQueries({
          queryKey: [projectId, "sessions", "report-jobs", sessionId],
        });
        queryClient.invalidateQueries({
          queryKey: queryKeys.artifacts.all(projectId),
        });
        invalidateSession();
      }
    },
  });

  const retryNodeMutation = useMutation({
    mutationFn: (nodeId: string) => api.control.rerunNode(sessionId, nodeId),
    onSuccess: invalidateSession,
  });

  const retryBlockedMutation = useMutation({
    mutationFn: (nodeId: string) => api.recovery.retry(sessionId, nodeId),
    onSuccess: invalidateSession,
  });

  const skipBlockedMutation = useMutation({
    mutationFn: (nodeId: string) => api.recovery.skip(sessionId, nodeId),
    onSuccess: invalidateSession,
  });

  return {
    pauseMutation,
    resumeMutation,
    forceResumeMutation,
    draftReportMutation,
    retryNodeMutation,
    retryBlockedMutation,
    skipBlockedMutation,
  };
}

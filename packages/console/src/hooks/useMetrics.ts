/**
 * React Query hooks for agent performance metrics API integration.
 *
 * All metrics endpoints are project-scoped (/projects/{id}/metrics/...).
 */

import { useQuery } from '@tanstack/react-query';
import { get, getApiProjectContext } from '@/lib/api';
import { queryKeys } from '@/lib/query-keys';
import { useProjectStore, selectCurrentProjectId } from '@/stores/project';

interface AgentMetrics {
  agent_name: string;
  total_executions: number;
  success_rate: number;
  avg_cost_usd: number;
  total_cost_usd: number;
  avg_tokens: number;
  avg_duration_seconds: number;
}

interface AgentMetricsResponse {
  agents: Record<string, AgentMetrics>;
  timeframe_hours?: number;
}

interface SessionMetrics {
  session_id: string;
  metrics: Array<{
    agent_name: string;
    model_name: string;
    node_id: string;
    feature_id?: string;
    started_at: string;
    completed_at?: string;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    total_cost_usd: number;
    success: boolean;
    error_type?: string;
    error_message?: string;
    duration_seconds: number;
  }>;
  summary: {
    total_executions: number;
    success_rate: number;
    total_cost_usd: number;
    total_tokens: number;
  };
}

interface FeatureMetrics {
  feature_id: string;
  agent_stats: Record<string, {
    executions: number;
    success_rate: number;
    avg_cost: number;
    total_cost: number;
    avg_tokens: number;
    avg_duration: number;
  }>;
  summary: {
    total_executions: number;
    success_rate: number;
    total_cost_usd: number;
    total_tokens: number;
  };
}

/** Build a project-scoped path for metrics endpoints. */
function metricsPath(path: string): string {
  const projectId = getApiProjectContext();
  if (!projectId) {
    throw new Error("No project selected. Call setApiProjectContext() first.");
  }
  return `/projects/${projectId}${path}`;
}

/**
 * Hook for fetching agent performance overview.
 */
export const useAgentMetrics = (timeframeHours?: number) => {
  const projectId = useProjectStore(selectCurrentProjectId);

  return useQuery<AgentMetricsResponse>({
    queryKey: queryKeys.metrics.agents(projectId!, timeframeHours),
    queryFn: () =>
      get<AgentMetricsResponse>(
        metricsPath('/metrics/agents'),
        timeframeHours ? { timeframe_hours: timeframeHours } : undefined,
      ),
    enabled: !!projectId,
    refetchInterval: 30000,
  });
};

/**
 * Hook for fetching specific agent performance.
 */
export const useAgentPerformance = (agentName: string, timeframeHours?: number) => {
  const projectId = useProjectStore(selectCurrentProjectId);

  return useQuery<AgentMetrics>({
    queryKey: queryKeys.metrics.agent(projectId!, agentName, timeframeHours),
    queryFn: () =>
      get<AgentMetrics>(
        metricsPath(`/metrics/agents/${agentName}`),
        timeframeHours ? { timeframe_hours: timeframeHours } : undefined,
      ),
    enabled: !!projectId && !!agentName,
  });
};

/**
 * Hook for fetching session metrics.
 */
export const useSessionMetrics = (sessionId: string) => {
  const projectId = useProjectStore(selectCurrentProjectId);

  return useQuery<SessionMetrics>({
    queryKey: [projectId, 'metrics', 'session', sessionId],
    queryFn: () => get<SessionMetrics>(metricsPath(`/metrics/sessions/${sessionId}`)),
    enabled: !!projectId && !!sessionId,
  });
};

/**
 * Hook for fetching feature metrics.
 */
export const useFeatureMetrics = (featureId: string) => {
  const projectId = useProjectStore(selectCurrentProjectId);

  return useQuery<FeatureMetrics>({
    queryKey: [projectId, 'metrics', 'feature', featureId],
    queryFn: () => get<FeatureMetrics>(metricsPath(`/metrics/features/${featureId}`)),
    enabled: !!projectId && !!featureId,
  });
};

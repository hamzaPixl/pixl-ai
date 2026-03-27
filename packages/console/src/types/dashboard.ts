import type { SessionListEntry, NodeInstance } from "./sessions";
import type { Event } from "./events-api";

export interface DashboardSummary {
  stats: {
    features: {
      total: number;
      backlog: number;
      planned: number;
      in_progress: number;
      review: number;
      blocked: number;
      done: number;
      failed: number;
      total_cost: number;
      total_tokens: number;
    };
    epics: {
      total: number;
      completed: number | null;
    };
    roadmaps: {
      total: number;
      completed: number | null;
    };
  };
  active_sessions: SessionListEntry[];
  recent_events: Event[];
  pending_gates: Array<NodeInstance & { session_id: string }>;
  autonomy?: {
    total_outcomes: number;
    avg_confidence: number;
    auto_approved_gates: number;
    manual_gate_approvals: number;
    gate_rejections: number;
    recovery_cycles: number;
    human_interventions: number;
  };
  chains?: {
    chains: {
      active_chains: number;
      running_chains: number;
      paused_chains: number;
      plan_ready_chains: number;
      plan_draft_chains: number;
      completed_chains: number;
      failed_chains: number;
      cancelled_chains: number;
      total_chains: number;
    };
    blocked_nodes: number;
    completion_rate_30d: number;
  };
  contracts?: {
    features: { complete: number; total: number; ratio: number };
    epics: { complete: number; total: number; ratio: number };
    overall: { complete: number; total: number; ratio: number };
  };
}

export interface ProgressResponse {
  total_features: number;
  status_counts: Record<string, number>;
  completion_pct: number;
  backlog_stats: Record<string, unknown>;
}

export interface CostBreakdown {
  total_cost_usd: number;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  by_model: Record<string, number>;
  by_agent: Record<string, number>;
}

export interface TimingStats {
  total_sessions: number;
  completed_sessions: number;
  failed_sessions: number;
  avg_session_duration_minutes: number | null;
  median_session_duration_minutes: number | null;
  avg_stage_duration_seconds: number | null;
  fastest_session_minutes: number | null;
  slowest_session_minutes: number | null;
}

export interface AgentOverview {
  agent_name: string;
  executions: number;
  success_rate: number;
  avg_cost_usd: number;
  total_cost_usd: number;
  avg_duration_seconds: number;
  total_tokens: number;
}

export interface RecoveryOverview {
  total_incidents: number;
  succeeded: number;
  failed: number;
  escalated: number;
  success_rate: number;
  top_errors: Array<{ error_type: string; count: number }>;
}

export interface DashboardOverview {
  project_name: string;
  stats: DashboardSummary["stats"];
  completion_pct: number;
  active_sessions: SessionListEntry[];
  recent_sessions: SessionListEntry[];
  recent_events: Event[];
  pending_gates: Array<NodeInstance & { session_id: string }>;
  autonomy: DashboardSummary["autonomy"];
  chains: DashboardSummary["chains"];
  contracts: DashboardSummary["contracts"];
  cost: CostBreakdown;
  timing: TimingStats;
  agents: AgentOverview[];
  recovery: RecoveryOverview;
}

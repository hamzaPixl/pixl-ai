import type { EpicStatus, ChainPlanStatus, ChainNodeStatus } from "./enums";

export interface Epic {
  id: string; // epic-XXX
  title: string;
  original_prompt: string;
  feature_ids: string[];
  workflow_id: string | null;
  status: EpicStatus;

  // Timestamps
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;

  // Tracking
  notes: string[];
}

export interface CreateEpicRequest {
  title: string;
  original_prompt?: string;
  workflow_id?: string | null;
  roadmap_id?: string | null;
  milestone_id?: number | null;
}

export interface UpdateEpicRequest {
  title?: string;
  original_prompt?: string;
  workflow_id?: string | null;
}

// Epic Execution Plan Types

export interface EpicExecutionPlanNode {
  node_id: string;
  feature_id: string | null;
  feature_ref: string;
  wave: number;
  parallel_group: number;
  owner: string | null;
  risk_class: "low" | "medium" | "high" | "critical" | null;
  estimate_points: number | null;
  status: ChainNodeStatus | null;
  session_id: string | null;
  attempt_count: number | null;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

export interface EpicExecutionPlanEdge {
  from: string;
  to: string;
}

export interface EpicExecutionPlanWave {
  wave: number;
  nodes: Array<{
    node_id: string;
    feature_ref: string;
    parallel_group: number;
    owner: string | null;
    risk_class: "low" | "medium" | "high" | "critical" | null;
    estimate_points: number | null;
    status: ChainNodeStatus | null;
    session_id: string | null;
    attempt_count: number | null;
    started_at: string | null;
    completed_at: string | null;
    error: string | null;
  }>;
}

export interface EpicExecutionPlanReadiness {
  ready: boolean;
  checks: Array<{
    id: string;
    ok: boolean;
    detail: string;
  }>;
  blockers: string[];
  dependency_issues: Array<{
    from: string;
    to: string;
    reason: string;
  }>;
  dangling_edges: string[];
}

export interface EpicExecutionPlan {
  chain_id: string;
  epic_id: string;
  mode: "plan_only";
  status: ChainPlanStatus;
  execution_policy: {
    max_parallel: number;
    failure_policy: "branch_aware" | string;
    stop_on_failure: boolean;
  };
  nodes: EpicExecutionPlanNode[];
  edges: EpicExecutionPlanEdge[];
  waves: EpicExecutionPlanWave[];
  validation_summary: {
    dag_valid: boolean;
    cycles_detected: string[];
    orphan_nodes: string[];
    notes: string[];
  };
  readiness: EpicExecutionPlanReadiness;
  updated_at: string | null;
  created_at: string | null;
}

// Epic Rollup (used by views)

export interface EpicRollup {
  id: string;
  title: string;
  status: EpicStatus;
  roadmap_id: string | null;
  created_at: string | null;
  completed_at: string | null;
  feature_count: number;
  features_by_status: Record<string, number>;
  active_runs: number;
  blockers: Array<{
    id: string;
    title: string;
    reason_type: "blocked" | "gate_waiting";
    blocked_reason: string | null;
  }>;
}

// Execution Chain Types

export interface ExecutionChainSummary {
  chain_id: string;
  epic_id: string;
  epic_title?: string;
  status: ChainPlanStatus;
  total_nodes: number;
  completed_nodes: number;
  failed_nodes: number;
  running_nodes: number;
  current_wave: number;
  total_waves: number;
  progress_pct: number;
  created_at: string | null;
  updated_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  nodes?: EpicExecutionPlanNode[];
  edges?: EpicExecutionPlanEdge[];
  waves?: EpicExecutionPlanWave[];
}

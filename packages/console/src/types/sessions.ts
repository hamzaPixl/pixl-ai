import type {
  SessionStatus,
  NodeState,
  FeatureType,
  SessionReportJobStatus,
  SessionReportTrigger,
} from "./enums";
import type { ArtifactMetadata, StageOutputPayload } from "./artifacts";
import type { WorkflowDetail } from "./workflows";

// Baton Context Types

export interface BatonArtifactRef {
  id: string;
  hash: string;
  type: string;
  summary_ref: string | null;
}

export interface BatonState {
  goal: string;
  current_state: string[];
  decision_log: string[];
  open_questions: string[];
  constraints: string[];
  artifacts: BatonArtifactRef[];
  work_scope: string[];
  acceptance: string[];
}

export interface BatonHistoryEntry {
  stage_id: string;
  timestamp: string;
  baton: BatonState;
  patch_applied: Record<string, unknown>;
}

export interface ContextSliceInfo {
  artifact_id: string;
  hash: string;
  layer: "summary" | "diff" | "excerpt" | "full";
  reason: string;
  token_estimate: number;
  excerpt_range: [number, number] | null;
}

export interface ContextAuditEntry {
  stage_id: string;
  timestamp: string;
  total_tokens: number;
  budget_tokens: number;
  utilization: number;
  slice_count: number;
  slices: ContextSliceInfo[];
}

// Session Types

export interface ExecutorCursor {
  current_node_id: string | null;
  ready_queue: string[];
  last_event_id: string | null;
}

export interface LoopState {
  current_iteration: number;
  max_iterations: number;
  history: Array<{
    iteration: number;
    from: string;
    to: string;
    via: string;
    timestamp: string;
  }>;
}

export interface NodeInstance {
  node_id: string;
  state: NodeState;
  attempt: number;
  ready_at: string | null;
  started_at: string | null;
  ended_at: string | null;
  blocked_reason: string | null;
  failure_kind: string | null;
  error_message: string | null;
  model_name: string | null;
  agent_name: string | null;

  // Optional metrics (present when enabled by backend)
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  cost_usd?: number;
}

export interface WorkflowSession {
  session_schema_version: number;
  id: string; // sess-XXXX
  feature_id: string;
  snapshot_hash: string;

  // Timestamps
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  last_updated_at: string | null;
  paused_at: string | null;
  pause_reason: string | null;

  // Runtime state
  node_instances: Record<string, NodeInstance>;
  loop_state: Record<string, LoopState>;
  executor_cursor: ExecutorCursor | null;

  // Git baseline
  baseline_commit: string | null;
  workspace_root: string | null;

  // Frozen artifacts
  frozen_artifacts: Record<string, string>;

  // Artifacts
  artifacts: ArtifactMetadata[];

  // Structured outputs (for structured context mode)
  structured_outputs: Record<string, StageOutputPayload>;
  session_state: Record<string, unknown>;

  // Baton context (null when not in baton mode)
  baton: BatonState | null;
  baton_history: BatonHistoryEntry[];
  context_audit: ContextAuditEntry[];

  // Status (computed, not stored)
  status: SessionStatus;
  is_orphaned: boolean;

  // Workflow snapshot for DAG rendering (attached by API, not stored in session)
  workflow_snapshot?: WorkflowDetail;
}

export interface SessionReportJob {
  id: string;
  session_id: string;
  trigger: SessionReportTrigger;
  terminal_status: "completed" | "failed" | null;
  status: SessionReportJobStatus;
  requested_by: string | null;
  artifact_id: string | null;
  error_message: string | null;
  retry_count: number;
  idempotency_key: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
}

export interface SessionListEntry {
  id: string;
  feature_id: string;
  status?: SessionStatus;
  created_at: string;
  feature_title?: string;
  feature_type?: FeatureType;
  parent_type?: "epic" | "roadmap";
  parent_id?: string;
  parent_title?: string;
  display_title?: string;
  // Fields returned by backend list endpoint but previously untyped
  node_instances?: Record<string, NodeInstance>;
  execution_seconds?: number;
  workflow_name?: string;
  workflow_id?: string;
  ended_at?: string | null;
  last_updated_at?: string | null;
  baseline_commit?: string | null;
  feature_status?: string;
  [key: string]: unknown;
}

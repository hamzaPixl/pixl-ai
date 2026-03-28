export interface LiveRunItem {
  session_id: string;
  feature_id: string | null;
  feature_title: string;
  current_node: string | null;
  node_state: string | null;
  started_at: string | null;
  elapsed_minutes: number | null;
}

export interface PendingGateItem {
  session_id: string;
  gate_id: string;
  feature_id: string | null;
  feature_title: string;
  waiting_since: string | null;
}

export interface RecoveringItem {
  session_id: string;
  node_id: string | null;
  attempt: number;
  feature_id: string | null;
  feature_title: string;
  started_at: string | null;
}

export interface RecentlyCompletedItem {
  id: string;
  title: string;
  completed_at: string | null;
  has_artifacts: boolean;
  contracts_clean: boolean;
}

export interface HealthView {
  success_rate: number;
  mean_recovery_minutes: number;
  top_failure_signatures: Array<{ error_type: string; count: number }>;
}

export interface FactoryHome {
  live_runs: LiveRunItem[];
  pending_gates: PendingGateItem[];
  recovering: RecoveringItem[];
  recently_completed: RecentlyCompletedItem[];
  health: HealthView;
  autonomy?: {
    total_outcomes: number;
    avg_confidence: number;
    auto_approved_gates: number;
    manual_gate_approvals: number;
    gate_rejections: number;
    recovery_cycles: number;
    human_interventions: number;
    autopilot_runs: number;
  };
}

// Swarm Types (chain signals, judge findings, quality scores)

export interface ChainSignal {
  id: number;
  chain_id: string;
  from_node: string;
  signal_type:
    | "file_modified"
    | "api_changed"
    | "blocker"
    | "discovery"
    | "status_update"
    | "file_claim"
    | "judge_finding";
  payload: Record<string, unknown>;
  created_at: string;
}

export interface ChainSignalListResponse {
  signals: ChainSignal[];
}

export interface JudgeFinding {
  category: string;
  severity: string;
  description: string;
  affected_nodes?: string[];
}

export interface JudgeVerdict {
  wave: number;
  verdict: "pass" | "warn" | "block";
  findings: JudgeFinding[];
}

export interface QualityScore {
  id: number;
  scope_type: string;
  scope_id: string;
  metric: string;
  value: number;
  measured_at: string;
}

export interface QualityScoresResponse {
  scores: QualityScore[];
}

export interface QualityLatestResponse {
  scope_type: string;
  scope_id: string;
  scores: Record<string, number>;
}

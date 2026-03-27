export interface RecoveryTimelineEntry {
  timestamp: string;
  event_type: string;
  node_id: string | null;
  data: Record<string, unknown>;
}

export interface RecoverySummary {
  total_recovery_events: number;
  retries: number;
  contract_repairs: number;
  escalations: number;
  successes: number;
}

export interface RecoveryTimeline {
  session_id: string;
  entries: RecoveryTimelineEntry[];
  summary: RecoverySummary;
}

export interface RecoveryInboxItem {
  session_id: string;
  node_id: string;
  blocked_reason: string;
  error_message: string | null;
  failure_kind: string | null;
  feature_id: string | null;
  feature_title: string;
  blocked_since: string | null;
  blocker_artifact: string | null;
  recovery_events: Array<Record<string, unknown>>;
}

export interface RecoveryInboxResponse {
  blockers: RecoveryInboxItem[];
}

export interface IncidentRecord {
  id: string;
  session_id: string;
  node_id: string | null;
  error_type: string;
  error_message: string;
  recovery_action: string | null;
  outcome: string;
  attempt_count: number;
  created_at: string;
  resolved_at: string | null;
  [key: string]: unknown;
}

export interface FailureSignature {
  error_type: string;
  count: number;
  last_seen: string;
}

export interface RecoveryActionRate {
  recovery_action: string;
  attempted: number;
  succeeded: number;
  rate: number;
}

export interface RecoveryTrendDay {
  day: string;
  total: number;
  succeeded: number;
  failed: number;
  escalated: number;
}

export interface HumanGateTrigger {
  feature_id: string;
  feature_title: string;
  escalation_count: number;
}

export interface RecoveryLabData {
  failure_signatures: FailureSignature[];
  recovery_success_rate: RecoveryActionRate[];
  trend: RecoveryTrendDay[];
  human_gate_triggers: HumanGateTrigger[];
}

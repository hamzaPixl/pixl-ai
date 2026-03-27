import type { RunStatus } from "./enums";

export interface UsageByModel {
  model: string;
  cost_usd: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  executions: number;
}

export interface UsageByAgent {
  agent: string;
  cost_usd: number;
  total_tokens: number;
  executions: number;
}

export interface UsageByFeature {
  feature_id: string;
  feature_title: string;
  cost_usd: number;
  total_tokens: number;
}

export interface ProjectUsageResponse {
  totals: {
    cost_usd: number;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  by_model: UsageByModel[];
  by_agent: UsageByAgent[];
  by_feature: UsageByFeature[];
}

// Heartbeat Run Types

export interface HeartbeatRun {
  id: string;
  session_id: string;
  status: RunStatus;
  started_at: string;
  ended_at: string | null;
  last_heartbeat_at: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
  adapter: string | null;
  model: string | null;
  error_message: string | null;
  baton: Record<string, unknown> | null;
}

// Budget Types

export interface BudgetConfig {
  monthly_usd: number;
  spent_monthly_usd: number;
  remaining_usd: number;
  is_exceeded: boolean;
}

export interface CostBreakdownEntry {
  adapter: string;
  model: string;
  session_count: number;
  total_tokens: number;
  cost_usd: number;
}

export interface CostBreakdownResponse {
  monthly_total_usd: number;
  breakdown: CostBreakdownEntry[];
}

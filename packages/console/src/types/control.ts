import type { AutonomyMode } from "./enums";

export interface AutonomyResponse {
  feature_id: string;
  mode: AutonomyMode;
}

export interface RerunResponse {
  status: string;
  node_id?: string;
  attempt?: number;
  reset_nodes?: string[];
}

export interface RollbackResponse {
  status: string;
  node_id: string;
  note: string;
}

export interface EpicWaveFeature {
  id: string;
  title: string;
  status: string | null;
}

export interface EpicWavesResponse {
  epic_id: string;
  total_waves: number;
  waves: EpicWaveFeature[][];
  error?: string;
}

export interface EpicExecutionProgressResult {
  feature_id: string | null;
  feature_ref: string | null;
  node_id: string;
  status: string;
  session_id: string | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface EpicExecutionProgressResponse {
  epic_id: string;
  chain_id?: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  total_features: number;
  completed_features: number;
  failed_features: number;
  current_wave: number;
  total_waves: number;
  progress_pct: number;
  results: EpicExecutionProgressResult[];
  error?: string | null;
}

export interface EpicRunRequest {
  workflow_id?: string;
  skip_approval?: boolean;
  parallel?: boolean;
  max_parallel?: number;
  stop_on_failure?: boolean;
}

export interface EpicRunResponse {
  status: string;
  epic_id: string;
  message: string;
}

export interface EpicCancelResponse {
  status: string;
  epic_id: string;
}

export interface ChainControlResponse {
  status: string;
  chain_id: string;
  epic_id: string;
}

export interface ChainStartResponse {
  status: string;
  chain_id: string;
  epic_id: string;
}

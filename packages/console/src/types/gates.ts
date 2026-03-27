import type { Event } from "./events-api";
import type { ArtifactMetadata } from "./artifacts";

export interface GateApproveRequest {
  note?: string | null;
}

export interface GateRejectRequest {
  reason?: string | null;
}

export interface GateResponse {
  node_id: string;
  state: string;
  [key: string]: unknown;
}

export interface GateInboxItem {
  session_id: string;
  gate_id: string;
  feature_id: string | null;
  feature_title: string;
  waiting_since: string | null;
  autonomy_mode?: "assist" | "autopilot";
  autonomy_profile?: {
    agent_name: string;
    task_key: string;
    level: number;
    confidence: number;
    samples: number;
    updated_at: string;
  } | null;
  evidence_bundle: {
    recent_events: Event[];
    artifacts: ArtifactMetadata[];
    contract_results: Event[];
  };
}

export interface GateInboxResponse {
  gates: GateInboxItem[];
}

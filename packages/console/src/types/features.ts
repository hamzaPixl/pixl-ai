import type { FeatureType, Priority, FeatureStatus } from "./enums";
import type { WorkflowSession } from "./sessions";
import type { NodeInstance } from "./sessions";
import type { Event } from "./events-api";
import type { ArtifactMetadata } from "./artifacts";

export interface Feature {
  id: string; // feat-XXX
  title: string;
  description: string;
  type: FeatureType;
  priority: Priority;
  status: FeatureStatus;

  // Timestamps (ISO 8601 strings)
  created_at: string;
  updated_at: string | null;
  planned_at: string | null;
  started_at: string | null;
  completed_at: string | null;

  // Parent references
  epic_id: string | null;
  roadmap_id: string | null;

  // Dependencies
  depends_on: string[];
  blocked_by: string | null;
  blocked_reason: string | null;

  // Tracking
  plan_path: string | null;
  pr_url: string | null;
  branch_name: string | null;

  // Metrics
  estimated_hours: number | null;
  actual_hours: number | null;
  total_cost_usd: number;
  total_tokens: number;

  // Verification
  success_criteria: string[];
  assumptions: string[];

  // Notes
  notes: string[];
}

export interface CreateFeatureRequest {
  title: string;
  description?: string;
  type?: FeatureType;
  priority?: Priority;
  depends_on?: string[];
  epic_id?: string | null;
  roadmap_id?: string | null;
}

export interface UpdateFeatureRequest {
  title?: string;
  description?: string;
  type?: FeatureType;
  priority?: Priority;
  depends_on?: string[];
}

// Transition Types

export interface TransitionRequest {
  to_status: string;
  trigger?: string;
  note?: string | null;
  blocked_by?: string | null;
  blocked_reason?: string | null;
}

export interface TransitionResponse {
  success: boolean;
  entity_id: string;
  from_status: string;
  to_status: string;
  error: string | null;
  warnings: string[];
}

export interface AvailableTransitions {
  entity_id: string;
  current_status: string;
  available: string[];
}

// Feature Progress Types (active session per feature)

export interface ActiveSessionData {
  session: {
    id: string;
    status: string;
    created_at: string;
  };
  current_node: {
    id: string;
    state: string;
    started_at: string;
  } | null;
  workflow: {
    id: string;
    name: string;
  } | null;
  stage_count: number;
  completed_stages: number;
}

export interface EvidenceView {
  contracts_passed: boolean;
  tests_passed: boolean;
  has_pr: boolean;
  has_plan: boolean;
}

export interface FeatureDetail extends Feature {
  current_session: WorkflowSession | null;
  pipeline: NodeInstance[];
  timeline: Event[];
  artifacts: ArtifactMetadata[];
  recovery_attempts: Array<Record<string, unknown>>;
  evidence: EvidenceView;
}

// Dependency Types

export interface DependencyGraph {
  graph: Record<string, string[]>;
}

export interface ExecutionOrder {
  epic_id: string;
  order: string[];
}

export interface DependencyCheck {
  feature_id: string;
  met: boolean;
  unmet: string[];
}

// Doctor Types

export interface DoctorCheck {
  name: string;
  status: string;
  message: string;
  details: Record<string, unknown>;
}

export interface DoctorReport {
  checks: DoctorCheck[];
  overall: string;
  timestamp: string;
}

// Knowledge Types

export interface KnowledgeSearchResult {
  chunk_id: string;
  title: string;
  content: string;
  [key: string]: unknown;
}

export interface KnowledgeStatus {
  [key: string]: unknown;
}

export interface KnowledgeSearchRequest {
  query: string;
  limit?: number;
  artifact_types?: import("./enums").ArtifactType[];
}

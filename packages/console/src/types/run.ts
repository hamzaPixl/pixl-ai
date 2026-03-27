export interface RunRequest {
  prompt: string;
  model?: string | null;
}

export interface ClassificationResponse {
  kind: "feature" | "epic" | "roadmap";
  confidence: number;
  title: string;
  suggested_workflow: string;
  estimated_features: number;
  why: string[];
  risk_flags: string[];
  suggested_sub_workflows: string[];
}

export interface ConfirmRunRequest {
  prompt: string;
  kind: "feature" | "epic" | "roadmap";
  title: string;
  workflow_id: string;
  skip_approval?: boolean;
}

export interface RunFeatureRequest {
  workflow_id: string;
  skip_approval?: boolean;
}

export interface RunStartResponse {
  session_id: string;
  entity_id: string;
  entity_kind: string;
  execution_feature_id?: string | null;
  status: string;
}

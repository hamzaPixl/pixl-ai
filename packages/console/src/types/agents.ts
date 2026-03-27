export interface AgentInfo {
  name: string;
  description: string;
  effective_model: string;
  default_model: string;
  has_override: boolean;
  override_model: string | null;
}

export interface UpdateAgentModelRequest {
  model: string | null; // null = reset to default
}

export interface ClassificationModelInfo {
  effective_model: string;
  default_model: string;
  has_override: boolean;
  override_model: string | null;
}

export interface UpdateClassificationModelRequest {
  model: string | null; // null = reset to default
}

export interface SessionReportModelInfo {
  effective_model: string;
  default_model: string;
  has_override: boolean;
  override_model: string | null;
}

export interface UpdateSessionReportModelRequest {
  model: string | null; // null = reset to default
}

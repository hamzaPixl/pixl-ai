import type { ArtifactType } from "./enums";

export interface ArtifactMetadata {
  id: string; // art-XXXX
  type: ArtifactType;
  name: string;
  path: string | null;

  // Hashes
  content_hash: string | null;
  logical_hash: string | null;

  // Provenance
  task_id: string;
  session_id: string;
  created_at: string;

  // Relationships
  references: string[];
  is_input_for: string[];

  // Additional metadata
  size_bytes: number | null;
  mime_type: string | null;
  tags: string[];
  extra: Record<string, unknown>;
}

export interface ArtifactResponse {
  id: number;
  name: string;
  artifact_type: string;
  [key: string]: unknown;
}

// Structured Output Types

export interface ArtifactWrittenRef {
  path: string;
  sha256: string;
  purpose: string;
}

export interface IncludedSourceRef {
  artifact_id: string;
  sha256: string;
  reason: string;
}

export interface StageErrorInfo {
  code: string;
  message: string;
  recoverable: boolean;
  details: Record<string, unknown>;
}

export interface StageOutputPayload {
  schema_version: string;
  stage_id: string;
  status: "ok" | "error";
  summary: string[];
  artifacts_written: ArtifactWrittenRef[];
  included_sources: IncludedSourceRef[];
  next: {
    recommended_stage: string;
    inputs_needed: string[];
  } | null;
  error: StageErrorInfo | null;
  payload: Record<string, unknown>;
}

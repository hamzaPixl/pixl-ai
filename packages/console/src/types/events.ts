/**
 * Server-Sent Events (SSE) types for real-time updates.
 *
 * Events are streamed from /api/events/stream or /api/events/stream/:sessionId
 */

import type { EventType } from "./api";

// Base SSE Event

export interface SSEEvent {
  id: string;
  event: string;
  data: SSEEventData;
  retry?: number;
}

export type SSEEventData =
  | SessionEventData
  | TaskEventData
  | GateEventData
  | ArtifactEventData
  | LoopEventData
  | ContractEventData
  | RecoveryEventData
  | EntityEventData
  | EntityCrudEventData
  | AutonomyEventData
  | SystemEventData
  | SDKEventData;

// Event Data Types

export interface BaseEventData {
  event_type: EventType;
  session_id?: string; // Optional for sessionless CRUD events
  node_id?: string;
  artifact_id?: string;
  created_at: string;
}

// Session events
export interface SessionEventData extends BaseEventData {
  event_type:
    | "session_created"
    | "session_started"
    | "session_paused"
    | "session_resumed"
    | "session_completed"
    | "session_failed"
    | "session_cancelled";
  reason?: string;
  error?: string;
  feature_id?: string;
}

// Task events
export interface TaskEventData extends BaseEventData {
  event_type:
    | "task_started"
    | "task_completed"
    | "task_failed"
    | "task_skipped"
    | "task_blocked"
    | "task_unblocked"
    | "task_retry_queued"
    | "task_paused"
    | "task_rolled_back";
  duration_seconds?: number;
  error?: string;
  failure_kind?: string;
  error_type?: string;
  error_metadata?: Record<string, unknown>;
  reason?: string;
  attempt?: number;
}

// Gate events
export interface GateEventData extends BaseEventData {
  event_type:
    | "gate_requested"
    | "gate_approved"
    | "gate_rejected"
    | "gate_timeout";
  artifacts?: string[];
  approver?: string;
  reason?: string;
  timeout_minutes?: number;
  note?: string;
}

// Artifact events
export interface ArtifactEventData extends BaseEventData {
  event_type:
    | "artifact_created"
    | "artifact_modified"
    | "artifact_frozen"
    | "frozen_artifact_violated"
    | "frozen_artifact_updated";
  artifact_id: string;
  path?: string;
  sha256?: string;
  expected_hash?: string;
  actual_hash?: string;
  old_hash?: string;
  new_hash?: string;
}

// Loop events
export interface LoopEventData extends BaseEventData {
  event_type: "loop_iteration" | "loop_max_reached";
  loop_id: string;
  iteration?: number;
  from?: string;
  to?: string;
  max_iterations?: number;
}

// Contract events
export interface ContractEventData extends BaseEventData {
  event_type:
    | "contract_violation"
    | "contract_warning"
    | "contract_passed"
    | "git_unavailable";
  violations?: string[];
  warning?: string;
  check?: string;
}

// Recovery events
export interface RecoveryEventData extends BaseEventData {
  event_type:
    | "recovery_requested"
    | "recovery_decision"
    | "recovery_succeeded"
    | "recovery_failed"
    | "recovery_escalated";
  action?: string;
  error_type?: string;
  attempt?: number;
  decision_reason?: string;
}

// Entity lifecycle events
export interface EntityEventData extends BaseEventData {
  event_type: "entity_status_changed";
  entity_id: string;
  entity_type?: "feature" | "epic" | "roadmap";
  from_status: string;
  to_status: string;
  trigger?: string;
  stage_id?: string;
}

// Entity CRUD events
export interface EntityCrudEventData extends BaseEventData {
  event_type:
    | "feature_created"
    | "feature_updated"
    | "feature_deleted"
    | "epic_created"
    | "epic_updated"
    | "roadmap_created"
    | "roadmap_updated"
    | "milestone_created";
  entity_id?: string;
  entity_type?: "feature" | "epic" | "roadmap";
  title?: string;
  updates?: Record<string, unknown>;
  epic_id?: string | null;
  roadmap_id?: string | null;
  milestone_id?: string;
  name?: string;
}

// Autonomy events
export interface AutonomyEventData extends BaseEventData {
  event_type: "autonomy_changed";
  entity_id?: string;
  entity_type?: "feature" | "epic";
  mode?: "assist" | "autopilot";
}

// System events
export interface SystemEventData extends BaseEventData {
  event_type: "checkpoint_saved" | "error";
  message?: string;
  is_transient?: boolean;
  cause?: string;
  metadata?: Record<string, unknown>;
}

// SDK-level events (for real-time tracing)
export interface SDKEventData extends BaseEventData {
  event_type:
    | "sdk_query_started"
    | "sdk_query_completed"
    | "sdk_tool_call_started"
    | "sdk_tool_call_completed"
    | "sdk_thinking_started"
    | "sdk_thinking_completed"
    | "sdk_text_delta"
    | "sdk_error";
  // sdk_query_started
  model?: string;
  prompt_preview?: string;
  // sdk_query_completed
  duration_seconds?: number;
  num_turns?: number;
  total_tokens?: number;
  // sdk_tool_call_*
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  is_error?: boolean;
  error_message?: string;
  // sdk_thinking_*
  thinking_preview?: string;
  // sdk_text_delta
  text?: string;
  // sdk_error
  error?: string;
  error_type?: string;
}

// SSE Message Format

/**
 * Format of SSE messages from the backend.
 * Each message is prefixed with "data: " and parsed as JSON.
 */
export interface SSEMessage {
  id: string;
  event_type: EventType;
  timestamp: string;
  session_id: string;
  node_id?: string;
  artifact_id?: string;
  payload?: Record<string, unknown>;
}

// Connection State

export type ConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "error";

export interface ConnectionInfo {
  status: ConnectionState;
  sessionId?: string;
  lastEventId?: string;
  reconnectAttempts: number;
  lastConnectedAt?: string;
  error?: string;
}

// Event Type Guards

export function isSessionEvent(data: SSEEventData): data is SessionEventData {
  return [
    "session_created",
    "session_started",
    "session_paused",
    "session_resumed",
    "session_completed",
    "session_failed",
    "session_cancelled",
  ].includes(data.event_type);
}

export function isTaskEvent(data: SSEEventData): data is TaskEventData {
  return [
    "task_started",
    "task_completed",
    "task_failed",
    "task_skipped",
    "task_blocked",
    "task_unblocked",
    "task_retry_queued",
    "task_paused",
    "task_rolled_back",
  ].includes(data.event_type);
}

export function isGateEvent(data: SSEEventData): data is GateEventData {
  return [
    "gate_requested",
    "gate_approved",
    "gate_rejected",
    "gate_timeout",
  ].includes(data.event_type);
}

export function isRecoveryEvent(data: SSEEventData): data is RecoveryEventData {
  return [
    "recovery_requested",
    "recovery_decision",
    "recovery_succeeded",
    "recovery_failed",
    "recovery_escalated",
  ].includes(data.event_type);
}

export function isEntityEvent(data: SSEEventData): data is EntityEventData {
  return data.event_type === "entity_status_changed";
}

export function isEntityCrudEvent(
  data: SSEEventData,
): data is EntityCrudEventData {
  return [
    "feature_created",
    "feature_updated",
    "feature_deleted",
    "epic_created",
    "epic_updated",
    "roadmap_created",
    "roadmap_updated",
    "milestone_created",
  ].includes(data.event_type);
}

export function isSDKEvent(data: SSEEventData): data is SDKEventData {
  return [
    "sdk_query_started",
    "sdk_query_completed",
    "sdk_tool_call_started",
    "sdk_tool_call_completed",
    "sdk_thinking_started",
    "sdk_thinking_completed",
    "sdk_text_delta",
    "sdk_error",
  ].includes(data.event_type);
}

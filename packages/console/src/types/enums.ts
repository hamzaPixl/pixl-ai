/**
 * Status and state enums matching backend Pydantic models.
 */

export type FeatureType =
  | "feature"
  | "bug"
  | "refactor"
  | "docs"
  | "chore"
  | "execution";

export type Priority = "P0" | "P1" | "P2" | "P3";

export type FeatureStatus =
  | "backlog"
  | "planned"
  | "in_progress"
  | "review"
  | "blocked"
  | "done"
  | "failed";

export type EpicStatus =
  | "drafting"
  | "decomposed"
  | "in_progress"
  | "completed"
  | "failed";

export type RoadmapStatus =
  | "drafting"
  | "planned"
  | "in_progress"
  | "completed";

export type MilestoneStatus =
  | "planned"
  | "in_progress"
  | "completed"
  | "failed";

export type SessionStatus =
  | "created"
  | "running"
  | "paused"
  | "stalled"
  | "failed"
  | "completed"
  | "cancelled";

export type NodeState =
  // Task node states
  | "task_pending"
  | "task_running"
  | "task_paused"
  | "task_completed"
  | "task_failed"
  | "task_blocked"
  | "task_skipped"
  // Gate node states
  | "gate_pending"
  | "gate_waiting"
  | "gate_approved"
  | "gate_rejected"
  | "gate_timeout"
  // Parallel/Merge node states
  | "parallel_waiting"
  | "parallel_ready"
  | "merge_waiting";

export type EventType =
  // Session events
  | "session_created"
  | "session_started"
  | "session_paused"
  | "session_resumed"
  | "session_reclaimed"
  | "session_completed"
  | "session_failed"
  | "session_cancelled"
  // Task events
  | "task_started"
  | "task_completed"
  | "task_failed"
  | "task_skipped"
  | "task_blocked"
  | "task_unblocked"
  | "task_retry_queued"
  | "task_paused"
  | "task_rolled_back"
  // Gate events
  | "gate_requested"
  | "gate_approved"
  | "gate_rejected"
  | "gate_timeout"
  // Artifact events
  | "artifact_created"
  | "artifact_modified"
  // Loop events
  | "loop_iteration"
  | "loop_max_reached"
  // Contract events
  | "contract_violation"
  | "contract_warning"
  | "contract_passed"
  | "git_unavailable"
  // Frozen artifact events
  | "artifact_frozen"
  | "frozen_artifact_violated"
  | "frozen_artifact_updated"
  // Entity lifecycle events
  | "entity_status_changed"
  // Entity CRUD events
  | "feature_created"
  | "feature_updated"
  | "feature_deleted"
  | "epic_created"
  | "epic_updated"
  | "roadmap_created"
  | "roadmap_updated"
  | "milestone_created"
  // Autonomy events
  | "autonomy_changed"
  // System events
  | "checkpoint_saved"
  | "error"
  // Recovery events
  | "recovery_requested"
  | "recovery_decision"
  | "recovery_succeeded"
  | "recovery_failed"
  | "recovery_escalated"
  | "recovery_no_runnable_node"
  // Structured output events
  | "structured_output_parsed"
  | "structured_output_invalid"
  // SDK-level events (for real-time tracing)
  | "sdk_query_started"
  | "sdk_query_completed"
  | "sdk_tool_call_started"
  | "sdk_tool_call_completed"
  | "sdk_thinking_started"
  | "sdk_thinking_completed"
  | "sdk_text_delta"
  | "sdk_error"
  // Session report events
  | "session_report_requested"
  | "session_report_generated"
  | "session_report_failed"
  // Swarm events
  | "chain_signal_emitted"
  | "chain_judge_blocked"
  | "chain_judge_passed";

export type ArtifactType =
  | "document"
  | "code"
  | "test"
  | "review"
  | "plan"
  | "context"
  | "requirement"
  | "diagram"
  | "log"
  | "progress"
  | "other";

export type ChainPlanStatus =
  | "plan_draft"
  | "plan_ready"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled";

export type ChainNodeStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "blocked"
  | "cancelled"
  | "refined";

export type RunStatus =
  | "active"
  | "completed"
  | "failed"
  | "stalled"
  | "cancelled";

export type SessionReportJobStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed";
export type SessionReportTrigger = "manual_draft" | "auto_terminal";

export type AutonomyMode = "assist" | "autopilot";

export type WorkItemType = "feature" | "epic" | "roadmap";

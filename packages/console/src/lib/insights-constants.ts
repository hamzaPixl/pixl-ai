import type { ArtifactType } from "@/types/api";

export const EVENT_PAGE_SIZE = 50;
export const ARTIFACTS_PAGE_SIZE = 30;

export const EVENT_CATEGORIES: Record<string, string[]> = {
  Session: [
    "session_created",
    "session_started",
    "session_paused",
    "session_resumed",
    "session_completed",
    "session_failed",
    "session_cancelled",
    "session_reclaimed",
  ],
  Task: [
    "task_started",
    "task_completed",
    "task_failed",
    "task_skipped",
    "task_blocked",
    "task_unblocked",
    "task_retry_queued",
    "task_paused",
    "task_rolled_back",
  ],
  Gate: ["gate_requested", "gate_approved", "gate_rejected", "gate_timeout"],
  Artifact: ["artifact_created", "artifact_modified", "artifact_frozen"],
  Recovery: [
    "recovery_requested",
    "recovery_decision",
    "recovery_succeeded",
    "recovery_failed",
    "recovery_escalated",
  ],
  Contract: ["contract_violation", "contract_warning", "contract_passed"],
  Entity: [
    "entity_status_changed",
    "feature_created",
    "feature_updated",
    "epic_created",
    "epic_updated",
    "roadmap_created",
  ],
};

export const eventTypeColor: Record<string, string> = {
  session_completed:
    "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  session_failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  task_completed:
    "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  task_failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  gate_approved:
    "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  gate_rejected: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  contract_violation:
    "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  recovery_escalated:
    "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300",
};

export const ARTIFACT_TYPES: ArtifactType[] = [
  "code",
  "test",
  "plan",
  "review",
  "document",
  "context",
  "requirement",
  "diagram",
  "log",
  "progress",
  "other",
];

export const TIMEFRAMES: { label: string; hours: number | undefined }[] = [
  { label: "24 hours", hours: 24 },
  { label: "7 days", hours: 168 },
  { label: "30 days", hours: 720 },
  { label: "All time", hours: undefined },
];

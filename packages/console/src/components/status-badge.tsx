/**
 * Status badge component with color coding and optional pulse animation.
 */

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type Status =
  | "backlog"
  | "planned"
  | "in_progress"
  | "review"
  | "blocked"
  | "done"
  | "failed"
  | "drafting"
  | "decomposed"
  | "completed"
  | "running"
  | "paused"
  | "stalled"
  | "created"
  | "cancelled"
  | "gate_waiting"
  | "gate_approved"
  | "gate_rejected"
  | "task_pending"
  | "task_running"
  | "task_completed"
  | "task_failed";

interface StatusBadgeProps {
  status: Status;
  className?: string;
}

const statusConfig: Record<
  Status,
  { variant: "default" | "success" | "warning" | "info" | "destructive" | "secondary"; label: string }
> = {
  // Feature statuses
  backlog: { variant: "secondary", label: "Backlog" },
  planned: { variant: "info", label: "Planned" },
  in_progress: { variant: "warning", label: "In Progress" },
  review: { variant: "info", label: "Review" },
  blocked: { variant: "destructive", label: "Blocked" },
  done: { variant: "success", label: "Done" },
  failed: { variant: "destructive", label: "Failed" },

  // Epic statuses
  drafting: { variant: "secondary", label: "Drafting" },
  decomposed: { variant: "info", label: "Decomposed" },

  // Common statuses
  completed: { variant: "success", label: "Completed" },
  running: { variant: "warning", label: "Running" },
  paused: { variant: "secondary", label: "Paused" },
  stalled: { variant: "warning", label: "Stalled" },
  created: { variant: "secondary", label: "Created" },
  cancelled: { variant: "destructive", label: "Cancelled" },

  // Gate statuses
  gate_waiting: { variant: "warning", label: "Awaiting Approval" },
  gate_approved: { variant: "success", label: "Approved" },
  gate_rejected: { variant: "destructive", label: "Rejected" },

  // Task statuses
  task_pending: { variant: "secondary", label: "Pending" },
  task_running: { variant: "warning", label: "Running" },
  task_completed: { variant: "success", label: "Completed" },
  task_failed: { variant: "destructive", label: "Failed" },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status] || { variant: "secondary", label: status };

  return (
    <Badge
      variant={config.variant}
      className={cn("capitalize", className)}
    >
      {config.label}
    </Badge>
  );
}

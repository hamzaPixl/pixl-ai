/**
 * RecentActivityFeed — vertical timeline of recent events.
 */

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Link } from "@tanstack/react-router";
import {
  Play,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Zap,
  FileText,
  RefreshCw,
  type LucideIcon,
} from "lucide-react";
import { formatTimeAgo } from "@/lib/format-utils";
import { humanize } from "./helpers";
import type { Event } from "@/types/api";
import type { EventType } from "@/types/enums";

const EVENT_META: Partial<
  Record<EventType, { icon: LucideIcon; color: string; label: string }>
> = {
  session_started: { icon: Play, color: "text-blue-500", label: "Session started" },
  session_completed: { icon: CheckCircle2, color: "text-green-500", label: "Session completed" },
  session_failed: { icon: XCircle, color: "text-red-500", label: "Session failed" },
  task_started: { icon: Zap, color: "text-blue-400", label: "Task started" },
  task_completed: { icon: CheckCircle2, color: "text-green-400", label: "Task completed" },
  task_failed: { icon: XCircle, color: "text-red-400", label: "Task failed" },
  gate_requested: { icon: ShieldAlert, color: "text-amber-500", label: "Gate requested" },
  gate_approved: { icon: ShieldCheck, color: "text-green-500", label: "Gate approved" },
  gate_rejected: { icon: ShieldAlert, color: "text-red-500", label: "Gate rejected" },
  artifact_created: { icon: FileText, color: "text-violet-500", label: "Artifact created" },
  contract_violation: { icon: AlertTriangle, color: "text-red-500", label: "Contract violation" },
  contract_passed: { icon: CheckCircle2, color: "text-green-400", label: "Contract passed" },
  task_blocked: { icon: AlertTriangle, color: "text-amber-500", label: "Task blocked" },
  task_retry_queued: { icon: RefreshCw, color: "text-amber-400", label: "Task retrying" },
};

const DEFAULT_META = { icon: Zap, color: "text-muted-foreground", label: "Event" };

interface RecentActivityFeedProps {
  events: Event[];
  projectId: string;
}

export function RecentActivityFeed({ events, projectId }: RecentActivityFeedProps) {
  const items = events.slice(0, 10);

  if (items.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground py-6 text-center">
            No recent activity
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
          <Link
            to="/project/$projectId/sessions"
            params={{ projectId }}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            View all
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-0">
          {items.map((event) => {
            const meta = EVENT_META[event.type] ?? DEFAULT_META;
            const Icon = meta.icon;
            const title =
              (event.data?.title as string) ??
              (event.node_id ? humanize(event.node_id) : meta.label);

            return (
              <div
                key={event.id}
                className="flex items-start gap-2 py-1.5 border-b border-border/50 last:border-0"
              >
                <Icon className={`h-3.5 w-3.5 mt-0.5 shrink-0 ${meta.color}`} />
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium truncate">{title}</p>
                  <p className="text-[10px] text-muted-foreground">
                    {meta.label}
                  </p>
                </div>
                <span className="text-[10px] text-muted-foreground shrink-0 tabular-nums">
                  {formatTimeAgo(event.timestamp)}
                </span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

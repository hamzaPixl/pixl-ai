/**
 * SessionsOverview — flat list of recent sessions, sorted by status.
 */

import { Link } from "@tanstack/react-router";
import { Clock } from "lucide-react";
import { StatusDot } from "@/components/status-dot";
import { formatTimeAgo, formatDuration } from "@/lib/format-utils";
import type { DashboardOverview } from "@/types/dashboard";

interface SessionsOverviewProps {
  data: DashboardOverview | undefined;
  projectId: string;
}

const STATUS_ORDER: Record<string, number> = {
  running: 0,
  paused: 1,
  pending: 2,
  completed: 3,
  failed: 4,
};

export function SessionsOverview({ data, projectId }: SessionsOverviewProps) {
  const sessions = data?.recent_sessions ?? [];

  if (sessions.length === 0) return null;

  const sorted = [...sessions].sort(
    (a, b) =>
      (STATUS_ORDER[a.status ?? "completed"] ?? 9) -
      (STATUS_ORDER[b.status ?? "completed"] ?? 9),
  );

  return (
    <section>
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-[11px] uppercase tracking-wider font-medium text-muted-foreground">
          Recent Sessions
        </h3>
        <span className="text-[10px] tabular-nums text-muted-foreground">
          {sessions.length}
        </span>
      </div>

      <div className="space-y-0.5">
        {sorted.slice(0, 8).map((s) => (
          <div
            key={s.id}
            className="flex items-center gap-2 py-1.5 text-xs rounded-md px-2 -mx-2 hover:bg-muted/50 transition-colors"
          >
            <StatusDot status={s.status ?? "completed"} />
            <span className="truncate flex-1 font-medium">
              {s.feature_id ? (
                <Link
                  to="/project/$projectId/features/$featureId"
                  params={{ projectId, featureId: s.feature_id }}
                  className="hover:underline"
                >
                  {s.display_title ?? s.feature_title ?? s.id.slice(0, 8)}
                </Link>
              ) : (
                s.display_title ?? s.feature_title ?? s.id.slice(0, 8)
              )}
            </span>
            {s.workflow_name && (
              <span className="text-[10px] text-muted-foreground truncate max-w-[100px]">
                {s.workflow_name}
              </span>
            )}
            {s.execution_seconds != null && s.execution_seconds > 0 && (
              <span className="text-muted-foreground flex items-center gap-0.5">
                <Clock className="h-3 w-3" />
                {formatDuration(s.execution_seconds)}
              </span>
            )}
            <span className="text-muted-foreground whitespace-nowrap">
              {formatTimeAgo(s.created_at)}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

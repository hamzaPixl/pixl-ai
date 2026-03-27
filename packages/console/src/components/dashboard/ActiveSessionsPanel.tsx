/**
 * ActiveSessionsPanel — flat list of running sessions, no card chrome.
 * Linear-style: section label, clean rows with hover highlight.
 */

import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { StatusDot } from "@/components/status-dot";
import { formatTimeAgo, formatDuration } from "@/lib/format-utils";
import { cn } from "@/lib/utils";
import type { SessionListEntry, HeartbeatRun } from "@/types/api";

interface ActiveSessionsPanelProps {
  sessions: SessionListEntry[];
  projectId: string;
  stalledRuns?: HeartbeatRun[];
}

export function ActiveSessionsPanel({
  sessions,
  projectId,
  stalledRuns,
}: ActiveSessionsPanelProps) {
  const stalledSessionIds = new Set(
    stalledRuns?.filter((r) => r.status === "stalled").map((r) => r.session_id),
  );

  return (
    <section>
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-[11px] uppercase tracking-wider font-medium text-muted-foreground">
          Active Sessions
        </h3>
        {sessions.length > 0 && (
          <span className="text-[10px] tabular-nums text-muted-foreground">
            {sessions.length}
          </span>
        )}
      </div>

      {sessions.length === 0 ? (
        <p className="text-xs text-muted-foreground py-4">No active sessions</p>
      ) : (
        <div className="space-y-0.5">
          {sessions.map((session) => {
            const isStalled = stalledSessionIds.has(session.id);
            const displayStatus = isStalled
              ? "stalled"
              : (session.status ?? "running");
            const elapsed = session.execution_seconds ?? 0;

            return (
              <Link
                key={session.id}
                to="/project/$projectId/sessions/$sessionId"
                params={{ projectId, sessionId: session.id }}
                className={cn(
                  "flex items-center gap-2 rounded-md px-2 py-1.5 text-xs -mx-2",
                  "hover:bg-muted/50 transition-colors",
                )}
              >
                <StatusDot status={displayStatus} />
                <span className="truncate font-medium min-w-0 flex-1">
                  {session.feature_id ? (
                    <Link
                      to="/project/$projectId/features/$featureId"
                      params={{ projectId, featureId: session.feature_id }}
                      className="hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {session.display_title ?? session.feature_title ?? session.id}
                    </Link>
                  ) : (
                    session.display_title ?? session.feature_title ?? session.id
                  )}
                </span>
                {session.workflow_name && (
                  <Badge
                    variant="outline"
                    className="text-[10px] px-1 py-0 shrink-0 border-border/50"
                  >
                    {session.workflow_name}
                  </Badge>
                )}
                <span className="text-muted-foreground shrink-0 tabular-nums">
                  {elapsed > 0
                    ? formatDuration(elapsed)
                    : formatTimeAgo(session.created_at)}
                </span>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}

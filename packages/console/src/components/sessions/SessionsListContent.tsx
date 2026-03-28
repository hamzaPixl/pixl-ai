/**
 * Sessions list — Linear-style compact rows with inline metadata.
 * Groups sessions by status with collapsible sections.
 */

import { useState, useMemo } from "react";
import { Link, useRouter } from "@tanstack/react-router";
import { useSessions } from "@/hooks/queries";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { StatusDot } from "@/components/status-dot";
import { StageProgressBar } from "@/components/inline-indicators";
import {
  formatTimeAgo,
  formatDuration,
  formatTokens,
} from "@/lib/format-utils";
import {
  Activity,
  ChevronRight,
  ChevronDown,
  Clock,
  DollarSign,
  Zap,
  Workflow,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { SessionListEntry } from "@/types/api";

const PAGE_SIZE = 100;

const STATUS_ORDER = [
  "running",
  "paused",
  "stalled",
  "created",
  "completed",
  "failed",
  "cancelled",
];

const STATUS_LABELS: Record<string, string> = {
  running: "Running",
  paused: "Paused",
  stalled: "Stalled",
  created: "Created",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
  unknown: "Unknown",
};

export interface SessionsListContentProps {
  projectId: string;
  selectedSessionId?: string | null;
  onSelectSession?: (id: string) => void;
}

export function SessionsListContent({
  projectId,
  selectedSessionId,
  onSelectSession,
}: SessionsListContentProps) {
  const router = useRouter();
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(
    new Set(),
  );

  const {
    data: sessions,
    isLoading,
    error,
  } = useSessions({ limit: PAGE_SIZE, offset: 0 }, projectId);

  const grouped = useMemo(() => {
    if (!sessions) return new Map<string, SessionListEntry[]>();
    const groups = new Map<string, SessionListEntry[]>();
    for (const st of STATUS_ORDER) {
      const items = sessions.filter((s) => (s.status ?? "unknown") === st);
      if (items.length > 0) groups.set(st, items);
    }
    const knownStatuses = new Set(STATUS_ORDER);
    const other = sessions.filter(
      (s) => !knownStatuses.has(s.status ?? "unknown"),
    );
    if (other.length > 0) groups.set("unknown", other);
    return groups;
  }, [sessions]);

  const toggleSection = (st: string) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(st)) next.delete(st);
      else next.add(st);
      return next;
    });
  };

  const handleClick = (sessionId: string) => {
    if (onSelectSession) {
      onSelectSession(sessionId);
    } else {
      router.navigate({
        to: "/project/$projectId/sessions/$sessionId",
        params: { projectId, sessionId },
      });
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-1">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 px-3 py-2.5">
            <Skeleton className="h-2 w-2 rounded-full shrink-0" />
            <Skeleton className="h-4 w-48" />
            <div className="flex-1" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-12" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border py-16 text-center text-destructive">
        Failed to load sessions
      </div>
    );
  }

  if (!sessions || sessions.length === 0) {
    return (
      <div className="rounded-lg border py-16 text-center text-muted-foreground">
        <Activity className="h-8 w-8 mx-auto mb-3 opacity-40" />
        <p className="text-sm">No sessions yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <TooltipProvider>
        <div className="space-y-1">
          {Array.from(grouped.entries()).map(([st, items]) => {
            const collapsed = collapsedSections.has(st);
            return (
              <div key={st}>
                <button
                  type="button"
                  onClick={() => toggleSection(st)}
                  className="flex items-center gap-2 w-full px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                  {collapsed ? (
                    <ChevronRight className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5" />
                  )}
                  <StatusDot status={st} />
                  <span className="uppercase tracking-wider">
                    {STATUS_LABELS[st] ?? st}
                  </span>
                  <span className="text-muted-foreground/60 tabular-nums">
                    {items.length}
                  </span>
                </button>

                {!collapsed && (
                  <div className="space-y-px">
                    {items.map((session) => (
                      <SessionRow
                        key={session.id}
                        session={session}
                        projectId={projectId}
                        isSelected={selectedSessionId === session.id}
                        onClick={() => handleClick(session.id)}
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </TooltipProvider>
    </div>
  );
}

function SessionRow({
  session,
  projectId,
  isSelected,
  onClick,
}: {
  session: SessionListEntry;
  projectId: string;
  isSelected: boolean;
  onClick: () => void;
}) {
  const title = session.display_title || session.feature_title || session.id;
  const nodes = session.node_instances ?? {};
  const totalTokens = Object.values(nodes).reduce(
    (sum: number, n: any) => sum + (n.total_tokens ?? 0),
    0,
  );
  const totalCost = Object.values(nodes).reduce(
    (sum: number, n: any) => sum + (n.cost_usd ?? 0),
    0,
  );
  const execSeconds = session.execution_seconds ?? 0;

  return (
    <div
      onClick={onClick}
      className={cn(
        "group flex items-center gap-3 px-3 py-2 rounded-md cursor-pointer transition-colors border border-transparent hover:border-border hover:bg-muted/50",
        isSelected && "bg-accent border-border",
      )}
    >
      {/* Status dot */}
      <StatusDot status={session.status ?? ""} />

      {/* Title + ID */}
      <div className="flex-1 min-w-0 flex items-center gap-2">
        <Link
          to="/project/$projectId/sessions/$sessionId"
          params={{ projectId, sessionId: session.id }}
          onClick={(e) => e.stopPropagation()}
          className="font-medium text-sm truncate hover:underline"
        >
          {title}
        </Link>
        <span className="text-[10px] text-muted-foreground/50 shrink-0 font-mono">
          {session.id.slice(-8)}
        </span>
      </div>

      {/* Metadata pills (right side) */}
      <div className="flex items-center gap-2 shrink-0 opacity-70 group-hover:opacity-100 transition-opacity">
        {/* Feature link */}
        {session.feature_id && (
          <Link
            to="/project/$projectId/features/$featureId"
            params={{ projectId, featureId: session.feature_id }}
            onClick={(e) => e.stopPropagation()}
          >
            <Badge
              variant="outline"
              className="text-[10px] px-1.5 py-0 h-5 max-w-[120px] truncate hover:bg-accent"
            >
              {session.feature_title || session.feature_id}
            </Badge>
          </Link>
        )}

        {/* Workflow badge */}
        {session.workflow_name && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0 h-5 gap-0.5"
              >
                <Workflow className="h-3 w-3" />
                {session.workflow_name}
              </Badge>
            </TooltipTrigger>
            <TooltipContent>Workflow</TooltipContent>
          </Tooltip>
        )}

        {/* Stage progress */}
        <div className="hidden sm:block w-24">
          <StageProgressBar nodes={nodes as any} />
        </div>

        {/* Duration */}
        {execSeconds > 0 && (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="text-[10px] text-muted-foreground tabular-nums flex items-center gap-0.5">
                <Clock className="h-3 w-3" />
                {formatDuration(execSeconds)}
              </span>
            </TooltipTrigger>
            <TooltipContent>Duration</TooltipContent>
          </Tooltip>
        )}

        {/* Tokens */}
        {totalTokens > 0 && (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="hidden md:flex text-[10px] text-muted-foreground tabular-nums items-center gap-0.5">
                <Zap className="h-3 w-3" />
                {formatTokens(totalTokens)}
              </span>
            </TooltipTrigger>
            <TooltipContent>Tokens</TooltipContent>
          </Tooltip>
        )}

        {/* Cost */}
        {totalCost > 0 && (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="text-[10px] text-muted-foreground tabular-nums flex items-center gap-0.5">
                <DollarSign className="h-3 w-3" />
                {totalCost.toFixed(2)}
              </span>
            </TooltipTrigger>
            <TooltipContent>Cost</TooltipContent>
          </Tooltip>
        )}

        {/* Time ago */}
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="text-[10px] text-muted-foreground tabular-nums">
              {formatTimeAgo(session.created_at)}
            </span>
          </TooltipTrigger>
          <TooltipContent>Created</TooltipContent>
        </Tooltip>
      </div>
    </div>
  );
}

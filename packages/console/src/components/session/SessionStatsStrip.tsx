import { ConnectionBadge } from "@/components/session";
import { Play, Workflow } from "lucide-react";
import type { StageInfo } from "@/lib/session-utils";
import type { WorkflowDetail, BatonHistoryEntry } from "@/types/api";

export interface SessionStatsStripProps {
  stages: StageInfo[];
  completedCount: number;
  runningCount: number;
  failedCount: number;
  waitingCount: number;
  progressPct: number;
  runtime: string | null;
  totalUsage: { cost: number; tokensIn: number; tokensOut: number };
  workflowSnapshot?: WorkflowDetail;
  isLive: boolean;
  connectionState: string;
  currentStage?: StageInfo;
  batonHistoryByStage: Map<string, BatonHistoryEntry>;
}

export function SessionStatsStrip({
  stages,
  completedCount,
  runningCount,
  failedCount,
  waitingCount,
  progressPct,
  runtime,
  totalUsage,
  workflowSnapshot,
  isLive,
  connectionState,
  currentStage,
  batonHistoryByStage,
}: SessionStatsStripProps) {
  if (stages.length === 0) return null;

  const pendingCount = stages.filter((s) => s.state === "pending").length;
  const activeBaton = currentStage
    ? batonHistoryByStage.get(currentStage.nodeId)
    : undefined;
  const hasUsageStats =
    !!runtime ||
    totalUsage.cost > 0 ||
    totalUsage.tokensIn > 0 ||
    totalUsage.tokensOut > 0;

  return (
    <div className="space-y-1.5">
      {/* Progress bar */}
      <div className="flex h-2 rounded-full overflow-hidden bg-muted">
        {completedCount > 0 && (
          <div
            className="bg-green-500 transition-all"
            style={{ width: `${(completedCount / stages.length) * 100}%` }}
          />
        )}
        {runningCount > 0 && (
          <div
            className="bg-blue-500 transition-all"
            style={{ width: `${(runningCount / stages.length) * 100}%` }}
          />
        )}
        {failedCount > 0 && (
          <div
            className="bg-red-500 transition-all"
            style={{ width: `${(failedCount / stages.length) * 100}%` }}
          />
        )}
        {waitingCount > 0 && (
          <div
            className="bg-yellow-500 transition-all"
            style={{ width: `${(waitingCount / stages.length) * 100}%` }}
          />
        )}
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-3 text-[11px] text-muted-foreground flex-wrap">
        <span className="tabular-nums font-medium text-foreground">
          {progressPct}%
        </span>
        <span className="tabular-nums">
          {completedCount}/{stages.length}
        </span>
        {completedCount > 0 && (
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-green-500" />
            {completedCount} done
          </span>
        )}
        {runningCount > 0 && (
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-blue-500" />
            {runningCount} running
          </span>
        )}
        {failedCount > 0 && (
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-red-500" />
            {failedCount} failed
          </span>
        )}
        {waitingCount > 0 && (
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-yellow-500" />
            {waitingCount} waiting
          </span>
        )}
        {pendingCount > 0 && (
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-muted-foreground/30" />
            {pendingCount} pending
          </span>
        )}

        {hasUsageStats && <Separator />}

        {runtime && <span className="tabular-nums">{runtime}</span>}
        {totalUsage.cost > 0 && (
          <span className="tabular-nums">${totalUsage.cost.toFixed(2)}</span>
        )}
        {(totalUsage.tokensIn > 0 || totalUsage.tokensOut > 0) && (
          <span className="tabular-nums hidden sm:inline">
            {totalUsage.tokensIn > 0 &&
              `${(totalUsage.tokensIn / 1000).toFixed(0)}k in`}
            {totalUsage.tokensIn > 0 && totalUsage.tokensOut > 0 && " / "}
            {totalUsage.tokensOut > 0 &&
              `${(totalUsage.tokensOut / 1000).toFixed(0)}k out`}
          </span>
        )}

        {workflowSnapshot && (
          <>
            <Separator />
            <span className="flex items-center gap-1">
              <Workflow className="h-3 w-3" />
              <span className="font-medium text-foreground">
                {workflowSnapshot.name}
              </span>
              {workflowSnapshot.version && (
                <span className="text-[10px]">v{workflowSnapshot.version}</span>
              )}
            </span>
          </>
        )}

        {isLive && (
          <>
            <Separator />
            <ConnectionBadge state={connectionState} />
          </>
        )}

        {currentStage && (
          <>
            <Separator />
            <span className="flex items-center gap-1">
              <Play className="h-3 w-3 text-blue-500" />
              <span className="font-medium text-foreground">
                {currentStage.nodeId}
              </span>
              {activeBaton?.baton.goal && (
                <span className="truncate max-w-[200px]">
                  — {activeBaton.baton.goal}
                </span>
              )}
            </span>
          </>
        )}
      </div>
    </div>
  );
}

function Separator() {
  return <span className="h-3 w-px bg-border" />;
}

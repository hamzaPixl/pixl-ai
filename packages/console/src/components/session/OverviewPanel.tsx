import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/status-badge";
import { ConnectionBadge } from "@/components/session";
import { Link } from "@tanstack/react-router";
import {
  Clock,
  Play,
  ShieldQuestion,
  FileText,
  Package,
  Check,
  X,
  Workflow,
} from "lucide-react";
import type { StageInfo } from "@/lib/session-utils";
import type {
  NodeInstance,
  ArtifactMetadata,
  BatonHistoryEntry,
  WorkflowDetail,
} from "@/types/api";

export interface OverviewPanelProps {
  projectId: string;
  session: any;
  sessionId: string;
  featureTitle?: string;
  executionFeature?: any;
  epic?: any;
  roadmap?: any;
  workflowSnapshot?: WorkflowDetail;
  connectionState: string;
  isLive: boolean;
  stages: StageInfo[];
  completedCount: number;
  runningCount: number;
  failedCount: number;
  waitingCount: number;
  progressPct: number;
  runtime: string | null;
  totalUsage: { cost: number; tokensIn: number; tokensOut: number };
  currentStage?: StageInfo;
  pendingGates: { nodeId: string; nodeInstance?: NodeInstance }[];
  artifacts?: ArtifactMetadata[];
  batonHistoryByStage: Map<string, BatonHistoryEntry>;
  onApproveGate: (gateId: string) => void;
  onRejectGate: (gateId: string) => void;
  onArtifactsClick: () => void;
}

export function OverviewPanel({
  projectId,
  session,
  sessionId,
  featureTitle,
  executionFeature,
  epic,
  roadmap,
  workflowSnapshot,
  connectionState,
  isLive,
  stages,
  completedCount,
  runningCount,
  failedCount,
  waitingCount,
  progressPct,
  runtime,
  totalUsage,
  currentStage,
  pendingGates,
  artifacts,
  batonHistoryByStage,
  onApproveGate,
  onRejectGate,
  onArtifactsClick,
}: OverviewPanelProps) {
  if (stages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground px-6">
        <Clock className="h-8 w-8 mb-3 opacity-50" />
        <p className="text-sm font-medium">Session not yet started</p>
        <p className="text-xs mt-1">
          Stages will appear here once execution begins.
        </p>
      </div>
    );
  }

  const pendingCount = stages.filter((s) => s.state === "pending").length;
  const activeBaton = currentStage
    ? batonHistoryByStage.get(currentStage.nodeId)
    : undefined;

  return (
    <div className="p-4 space-y-4">
      <div className="space-y-2">
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground flex-wrap">
          <span className="font-mono">{sessionId}</span>
          {session?.feature_id && featureTitle !== session.feature_id && (
            <>
              <span className="text-muted-foreground/40">&middot;</span>
              <Link
                to="/project/$projectId/features/$featureId"
                params={{ projectId, featureId: session.feature_id }}
                className="font-mono hover:underline"
              >
                {session.feature_id}
              </Link>
            </>
          )}
          {executionFeature?.epic_id && (
            <>
              <span className="text-muted-foreground/40">&middot;</span>
              <Badge variant="secondary" className="text-[10px] px-1 h-4">
                Epic
              </Badge>
              <span className="font-mono">{executionFeature.epic_id}</span>
              {epic?.title && (
                <span className="truncate max-w-[180px]">{epic.title}</span>
              )}
            </>
          )}
          {executionFeature?.roadmap_id && (
            <>
              <span className="text-muted-foreground/40">&middot;</span>
              <Badge variant="secondary" className="text-[10px] px-1 h-4">
                Roadmap
              </Badge>
              <span className="font-mono">{executionFeature.roadmap_id}</span>
              {roadmap?.title && (
                <span className="truncate max-w-[180px]">{roadmap.title}</span>
              )}
            </>
          )}
        </div>

        <div className="flex items-center gap-2 text-xs">
          {workflowSnapshot && (
            <span className="flex items-center gap-1 text-muted-foreground">
              <Workflow className="h-3 w-3" />
              <span className="font-medium text-foreground">
                {workflowSnapshot.name}
              </span>
              {workflowSnapshot.version && (
                <span className="text-[10px]">v{workflowSnapshot.version}</span>
              )}
            </span>
          )}
          {isLive && (
            <span className="ml-auto">
              <ConnectionBadge state={connectionState} />
            </span>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          {session && <StatusBadge status={session.status} />}
          {runtime && (
            <span className="text-xs text-muted-foreground">{runtime}</span>
          )}
          {totalUsage.cost > 0 && (
            <span className="text-xs text-muted-foreground tabular-nums ml-auto">
              ${totalUsage.cost.toFixed(2)}
            </span>
          )}
        </div>

        <div className="space-y-1.5">
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
          </div>
        </div>

        {(totalUsage.tokensIn > 0 || totalUsage.tokensOut > 0) && (
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            {totalUsage.tokensIn > 0 && (
              <span className="tabular-nums">
                {(totalUsage.tokensIn / 1000).toFixed(0)}k in
              </span>
            )}
            {totalUsage.tokensIn > 0 && totalUsage.tokensOut > 0 && (
              <span className="text-muted-foreground/50">/</span>
            )}
            {totalUsage.tokensOut > 0 && (
              <span className="tabular-nums">
                {(totalUsage.tokensOut / 1000).toFixed(0)}k out
              </span>
            )}
          </div>
        )}
      </div>

      {currentStage && (
        <div className="rounded-md border bg-blue-500/5 border-blue-500/20 p-3 space-y-1">
          <div className="flex items-center gap-2">
            <Play className="h-3.5 w-3.5 text-blue-500" />
            <span className="text-xs font-medium">Active Stage</span>
          </div>
          <p className="text-sm font-medium pl-5">{currentStage.nodeId}</p>
          {currentStage.attempt > 1 && (
            <Badge variant="outline" className="text-[10px] px-1 ml-5">
              Attempt #{currentStage.attempt}
            </Badge>
          )}
          {activeBaton?.baton.goal && (
            <p className="text-xs text-muted-foreground pl-5 mt-1">
              {activeBaton.baton.goal}
            </p>
          )}
        </div>
      )}

      {pendingGates.length > 0 && (
        <div className="space-y-2">
          <span className="text-xs font-medium text-yellow-600 flex items-center gap-1.5">
            <ShieldQuestion className="h-3.5 w-3.5" />
            Pending Gates
          </span>
          {pendingGates.map((gate) => (
            <div
              key={gate.nodeId}
              className="rounded-md border border-yellow-500/30 bg-yellow-500/5 p-3"
            >
              <p className="text-xs font-medium mb-2">{gate.nodeId}</p>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-1 text-destructive hover:bg-destructive hover:text-destructive-foreground h-7 text-xs"
                  onClick={() => onRejectGate(gate.nodeId)}
                >
                  <X className="h-3 w-3 mr-1" />
                  Reject
                </Button>
                <Button
                  size="sm"
                  className="flex-1 bg-green-600 hover:bg-green-700 h-7 text-xs"
                  onClick={() => onApproveGate(gate.nodeId)}
                >
                  <Check className="h-3 w-3 mr-1" />
                  Approve
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {artifacts && artifacts.length > 0 && (
        <div className="space-y-1.5">
          <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
            <Package className="h-3.5 w-3.5" />
            Artifacts
          </span>
          <div className="space-y-0.5">
            {artifacts.slice(0, 6).map((art) => {
              const filename =
                (art.path || art.name).split("/").pop() || art.path || art.name;
              return (
                <div
                  key={art.id}
                  className="flex items-center gap-2 px-2 py-1 rounded hover:bg-muted/50 text-xs"
                >
                  <FileText className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                  <span className="truncate flex-1 font-mono text-[11px]">
                    {filename}
                  </span>
                  <Badge variant="outline" className="text-[9px] px-1 h-3.5">
                    {art.type}
                  </Badge>
                </div>
              );
            })}
          </div>
          <button
            className="text-[11px] text-primary hover:underline pl-2"
            onClick={onArtifactsClick}
          >
            {artifacts.length > 6
              ? `View all ${artifacts.length} artifacts`
              : "View artifacts"}
          </button>
        </div>
      )}

      {activeBaton && activeBaton.baton.current_state.length > 0 && (
        <div className="space-y-1.5">
          <span className="text-xs font-medium text-muted-foreground">
            Baton State
          </span>
          <ul className="space-y-0.5">
            {activeBaton.baton.current_state.slice(0, 4).map((item, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs">
                <span className="text-muted-foreground/60 mt-0.5">-</span>
                <span>{item}</span>
              </li>
            ))}
            {activeBaton.baton.current_state.length > 4 && (
              <li className="text-[11px] text-muted-foreground pl-4">
                +{activeBaton.baton.current_state.length - 4} more
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

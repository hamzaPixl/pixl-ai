import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/status-badge";
import { ArtifactDrawerContent } from "@/components/session";
import { ArrowLeft, Package, Workflow } from "lucide-react";
import type { UnifiedNode, PanelMode } from "@/lib/session-constants";
import { STATE_ICONS } from "@/lib/session-constants";
import type { StageInfo } from "@/lib/session-utils";
import type {
  NodeInstance,
  StageOutputPayload,
  BatonHistoryEntry,
  ContextAuditEntry,
  ArtifactMetadata,
  WorkflowDetail,
} from "@/types/api";
import { OverviewPanel } from "@/components/session/OverviewPanel";
import { NodeDetailDrawer } from "@/components/session/NodeDetailDrawer";

export interface RightPanelProps {
  panel: PanelMode;
  setPanel: (p: PanelMode) => void;
  session: any;
  stages: StageInfo[];
  selectedUnifiedNode?: UnifiedNode;
  structuredOutputs: Record<string, StageOutputPayload>;
  batonHistoryByStage: Map<string, BatonHistoryEntry>;
  contextAuditByStage: Map<string, ContextAuditEntry>;
  artifacts?: ArtifactMetadata[];
  projectId: string;
  sessionId: string;
  isLive: boolean;
  connectionState: string;
  workflowSnapshot?: WorkflowDetail;
  featureTitle?: string;
  executionFeature?: any;
  epic?: any;
  roadmap?: any;
  totalUsage: { cost: number; tokensIn: number; tokensOut: number };
  completedCount: number;
  runningCount: number;
  failedCount: number;
  waitingCount: number;
  progressPct: number;
  runtime: string | null;
  currentStage?: StageInfo;
  pendingGates: { nodeId: string; nodeInstance?: NodeInstance }[];
  onArtifactsClick: () => void;
  onApproveGate: (gateId: string) => void;
  onRejectGate: (gateId: string) => void;
  onRetryNode: (nodeId: string) => void;
}

export function RightPanel({
  panel,
  setPanel,
  session,
  stages,
  selectedUnifiedNode,
  structuredOutputs,
  batonHistoryByStage,
  contextAuditByStage,
  artifacts,
  projectId,
  sessionId,
  isLive,
  connectionState,
  workflowSnapshot,
  featureTitle,
  executionFeature,
  epic,
  roadmap,
  totalUsage,
  completedCount,
  runningCount,
  failedCount,
  waitingCount,
  progressPct,
  runtime,
  currentStage,
  pendingGates,
  onArtifactsClick,
  onApproveGate,
  onRejectGate,
  onRetryNode,
}: RightPanelProps) {
  return (
    <>
      <div className="px-4 py-3 border-b shrink-0 flex items-center gap-2">
        {panel.mode !== "overview" && (
          <button
            className="h-6 w-6 flex items-center justify-center rounded hover:bg-muted transition-colors"
            onClick={() => setPanel({ mode: "overview" })}
          >
            <ArrowLeft className="h-3.5 w-3.5" />
          </button>
        )}

        {panel.mode === "overview" && (
          <>
            <Workflow className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Session Overview</span>
          </>
        )}

        {panel.mode === "node" && selectedUnifiedNode && (
          <>
            {STATE_ICONS[selectedUnifiedNode.state]}
            <span className="text-sm font-medium truncate">{panel.nodeId}</span>
            <StatusBadge status={selectedUnifiedNode.state as any} />
          </>
        )}

        {panel.mode === "artifact" && (
          <>
            <Package className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Artifacts</span>
            {artifacts && (
              <Badge variant="secondary" className="text-[10px] px-1 h-4">
                {artifacts.length}
              </Badge>
            )}
          </>
        )}
      </div>

      {panel.mode === "overview" && (
        <div className="flex-1 min-h-0 overflow-y-auto">
          <OverviewPanel
            projectId={projectId}
            session={session}
            sessionId={sessionId}
            featureTitle={featureTitle}
            executionFeature={executionFeature}
            epic={epic}
            roadmap={roadmap}
            workflowSnapshot={workflowSnapshot}
            connectionState={connectionState}
            isLive={isLive}
            stages={stages}
            completedCount={completedCount}
            runningCount={runningCount}
            failedCount={failedCount}
            waitingCount={waitingCount}
            progressPct={progressPct}
            runtime={runtime}
            totalUsage={totalUsage}
            currentStage={currentStage}
            pendingGates={pendingGates}
            artifacts={artifacts}
            batonHistoryByStage={batonHistoryByStage}
            onApproveGate={onApproveGate}
            onRejectGate={onRejectGate}
            onArtifactsClick={onArtifactsClick}
          />
        </div>
      )}

      {panel.mode === "node" && selectedUnifiedNode && (
        <NodeDetailDrawer
          node={selectedUnifiedNode}
          structuredOutput={structuredOutputs[selectedUnifiedNode.nodeId]}
          batonEntry={batonHistoryByStage.get(selectedUnifiedNode.nodeId)}
          contextAudit={contextAuditByStage.get(selectedUnifiedNode.nodeId)}
          onApprove={
            selectedUnifiedNode.state === "waiting"
              ? () => onApproveGate(selectedUnifiedNode.nodeId)
              : undefined
          }
          onReject={
            selectedUnifiedNode.state === "waiting"
              ? () => onRejectGate(selectedUnifiedNode.nodeId)
              : undefined
          }
          onRetryNode={
            selectedUnifiedNode.state === "failed"
              ? () => onRetryNode(selectedUnifiedNode.nodeId)
              : undefined
          }
        />
      )}

      {panel.mode === "artifact" && (
        <>
          {artifacts && artifacts.length > 0 ? (
            <ArtifactDrawerContent
              artifacts={artifacts}
              frozenArtifacts={session?.frozen_artifacts}
              selectedArtifactId={panel.artifactId}
              sessionId={sessionId}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground">
              No artifacts yet
            </div>
          )}
        </>
      )}
    </>
  );
}

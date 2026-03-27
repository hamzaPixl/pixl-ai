/**
 * Session detail route — unified single-column layout.
 *
 * Sticky header (breadcrumb + title + stats), then a single scrollable
 * area with collapsible DAG, node list, and collapsible artifacts.
 */

import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useMemo, useRef, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSessionTrace } from "@/hooks/use-session-trace";
import { useApproveGate, useRejectGate } from "@/hooks/queries/use-gates";
import { useSessionMutations } from "@/hooks/use-session-mutations";
import { useSessionComputed } from "@/hooks/use-session-computed";
import { queryKeys } from "@/lib/query-keys";
import { ApiRequestError } from "@/lib/api";
import { api } from "@/lib/api";
import { WorkflowPipeline } from "@/components/WorkflowPipeline";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { NeedsAttentionRail } from "@/components/session";
import { StatusBadge } from "@/components/status-badge";
import { SessionStatsStrip } from "@/components/session/SessionStatsStrip";
import { ArtifactDrawerContent } from "@/components/session/ArtifactDrawerContent";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  ArrowLeft,
  Pause,
  Play,
  Clock,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  Zap,
  Package,
} from "lucide-react";

import { NodeRow } from "@/components/session/NodeRow";

export const Route = createFileRoute("/project/$projectId/sessions/$sessionId")(
  {
    component: SessionDetailPage,
  },
);

function SessionDetailPage() {
  const { projectId, sessionId } = Route.useParams();
  const queryClient = useQueryClient();
  const traceEndRef = useRef<HTMLDivElement>(null);

  const [dagCollapsed, setDagCollapsed] = useState(false);
  const [artifactsOpen, setArtifactsOpen] = useState(false);

  const {
    data: session,
    isLoading: sessionLoading,
    error: sessionError,
  } = useQuery({
    queryKey: queryKeys.sessions.detail(projectId!, sessionId),
    queryFn: () => api.sessions.get(sessionId),
    enabled: !!projectId,
    refetchInterval: (query) => {
      const s = query.state.data;
      if (
        s?.status === "running" ||
        s?.status === "stalled" ||
        s?.status === "created"
      )
        return 3000;
      if (
        s?.status === "completed" ||
        s?.status === "failed" ||
        s?.status === "cancelled"
      )
        return false;
      return false;
    },
  });

  const { data: executionFeature } = useQuery({
    queryKey: queryKeys.features.detail(projectId!, session?.feature_id ?? ""),
    queryFn: () => api.features.get(session!.feature_id),
    enabled: !!projectId && !!session?.feature_id,
  });

  const { data: artifacts } = useQuery({
    queryKey: queryKeys.artifacts.list(projectId!, { session_id: sessionId }),
    queryFn: () => api.artifacts.list({ session_id: sessionId }),
    enabled: !!projectId,
    refetchInterval: () => {
      const status = session?.status;
      return status === "running" ||
        status === "paused" ||
        status === "stalled" ||
        status === "created"
        ? 5000
        : false;
    },
  });

  const isLive =
    session?.status === "running" ||
    session?.status === "paused" ||
    session?.status === "stalled" ||
    session?.status === "created";

  const { events, isConnected, connectionState, isLoadingHistory } =
    useSessionTrace(sessionId, isLive ?? true, projectId);

  const approveGate = useApproveGate(projectId);
  const rejectGate = useRejectGate(projectId);

  const {
    pauseMutation,
    resumeMutation,
    forceResumeMutation,
    retryNodeMutation,
    retryBlockedMutation,
    skipBlockedMutation,
  } = useSessionMutations(sessionId, projectId!, queryClient);

  const {
    stages,
    currentStage,
    pendingGates,
    failedNodes,
    blockedNodes,
    unifiedNodes,
    nodeExecutionStates,
    structuredOutputs,
    batonHistoryByStage,
    contextAuditByStage,
    isStalled,
    isOrphaned,
    isFailed,
    runtime,
    completedCount,
    failedCount,
    runningCount,
    waitingCount,
    progressPct,
    featureTitle,
    workflowSnapshot,
    hasDAG,
    totalUsage,
  } = useSessionComputed(session, events, executionFeature);

  const resumeErrorDetail = useMemo(() => {
    const err = resumeMutation.error;
    if (!err || !(err instanceof ApiRequestError) || err.status !== 409)
      return null;
    return err.body as import("@/components/session/NeedsAttentionRail").ResumeErrorDetail;
  }, [resumeMutation.error]);

  const canPause =
    session?.status === "running" && !isOrphaned && !pauseMutation.isPending;
  const canResume =
    (session?.status === "paused" || isStalled || isOrphaned || isFailed) &&
    !resumeMutation.isPending;
  useEffect(() => {
    if (isLive && !hasDAG && traceEndRef.current) {
      traceEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [events.length, isLive, hasDAG]);

  if (sessionError) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <p className="text-destructive">
          Failed to load session: {(sessionError as Error).message}
        </p>
        <Link to="/project/$projectId/sessions" params={{ projectId }}>
          <Button variant="outline" className="mt-4">
            Back to Sessions
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Sticky header zone */}
      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm pb-2 space-y-2">
        {/* Breadcrumb */}
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <Link
            to="/project/$projectId/sessions"
            params={{ projectId }}
            className="hover:text-foreground transition-colors flex items-center gap-1"
          >
            <ArrowLeft className="h-3 w-3" />
            Sessions
          </Link>
          <ChevronRight className="h-3 w-3" />
          <span className="font-mono">{sessionId.slice(0, 12)}</span>
        </div>

        {/* Title + status + controls */}
        <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
          <h2 className="text-base sm:text-lg font-semibold truncate min-w-0">
            {featureTitle}
          </h2>
          {session && <StatusBadge status={session.status} />}

          <div className="flex items-center gap-2 ml-auto flex-shrink-0">
            {canPause && (
              <Button
                variant="outline"
                size="default"
                onClick={() => pauseMutation.mutate()}
                disabled={pauseMutation.isPending}
              >
                <Pause className="h-4 w-4 mr-1.5" />
                Pause
              </Button>
            )}
            {canResume && (
              <Button
                variant="default"
                size="default"
                onClick={() => resumeMutation.mutate()}
                disabled={resumeMutation.isPending}
              >
                <Play className="h-4 w-4 mr-1.5" />
                Resume
              </Button>
            )}
            {resumeErrorDetail?.suggestion === "force_resume" && (
              <Button
                variant="destructive"
                size="default"
                onClick={() => forceResumeMutation.mutate()}
                disabled={forceResumeMutation.isPending}
              >
                <Zap className="h-4 w-4 mr-1.5" />
                Force Resume
              </Button>
            )}
          </div>
        </div>

        {/* Stats strip */}
        <SessionStatsStrip
          stages={stages}
          completedCount={completedCount}
          runningCount={runningCount}
          failedCount={failedCount}
          waitingCount={waitingCount}
          progressPct={progressPct}
          runtime={runtime}
          totalUsage={totalUsage}
          workflowSnapshot={workflowSnapshot}
          isLive={isLive ?? false}
          connectionState={connectionState}
          currentStage={currentStage}
          batonHistoryByStage={batonHistoryByStage}
        />
      </div>

      {/* Attention rail */}
      <NeedsAttentionRail
        isStalled={isStalled ?? false}
        isOrphaned={isOrphaned ?? false}
        pendingGates={pendingGates}
        failedNodes={failedNodes}
        blockedNodes={blockedNodes}
        onResume={() => resumeMutation.mutate()}
        isResumePending={resumeMutation.isPending}
        onApproveGate={(gateId) => approveGate.mutate({ sessionId, gateId })}
        onRejectGate={(gateId) => rejectGate.mutate({ sessionId, gateId })}
        onRetryNode={(nodeId) => retryNodeMutation.mutate(nodeId)}
        onRetryBlockedNode={(nodeId) => retryBlockedMutation.mutate(nodeId)}
        onSkipNode={(nodeId) => skipBlockedMutation.mutate(nodeId)}
        isRetryPending={
          retryNodeMutation.isPending ||
          retryBlockedMutation.isPending ||
          skipBlockedMutation.isPending
        }
        onForceResume={() => forceResumeMutation.mutate()}
        isForceResumePending={forceResumeMutation.isPending}
        resumeError={resumeErrorDetail}
      />

      {/* Scrollable content */}
      <div className="flex-1 min-h-0 overflow-y-auto space-y-3 mt-2">
        {sessionLoading || isLoadingHistory ? (
          <div className="space-y-2 max-w-md mx-auto px-8 py-12">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : (
          <>
            {/* Collapsible DAG */}
            {hasDAG && (
              <div className="rounded-lg border bg-muted/20 overflow-hidden">
                <button
                  className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-muted/30 transition-colors"
                  onClick={() => setDagCollapsed((v) => !v)}
                >
                  {dagCollapsed ? (
                    <ChevronRight className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5" />
                  )}
                  Pipeline DAG
                </button>
                {!dagCollapsed && (
                  <div className="h-[300px] border-t">
                    <WorkflowPipeline
                      workflow={workflowSnapshot!}
                      selectedNode={null}
                      hoveredNode={null}
                      onSelect={() => {}}
                      onHover={() => {}}
                      activeType={null}
                      nodeStates={nodeExecutionStates}
                      nodeInstances={session?.node_instances}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Node list */}
            {unifiedNodes.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                {isLive ? (
                  <>
                    <RefreshCw className="h-8 w-8 mb-2 animate-spin" />
                    <p>
                      {isConnected
                        ? "Waiting for execution to start..."
                        : "Connecting to event stream..."}
                    </p>
                  </>
                ) : (
                  <>
                    <Clock className="h-8 w-8 mb-2" />
                    <p>No execution data</p>
                  </>
                )}
              </div>
            ) : (
              <div className="space-y-1">
                {unifiedNodes.map((node) => (
                  <NodeRow
                    key={node.nodeId}
                    node={node}
                    structuredOutput={structuredOutputs[node.nodeId]}
                    batonEntry={batonHistoryByStage.get(node.nodeId)}
                    contextAudit={contextAuditByStage.get(node.nodeId)}
                    onApprove={
                      node.state === "waiting"
                        ? () =>
                            approveGate.mutate({
                              sessionId,
                              gateId: node.nodeId,
                            })
                        : undefined
                    }
                    onReject={
                      node.state === "waiting"
                        ? () =>
                            rejectGate.mutate({
                              sessionId,
                              gateId: node.nodeId,
                            })
                        : undefined
                    }
                    onRetryNode={
                      node.state === "failed"
                        ? () => retryNodeMutation.mutate(node.nodeId)
                        : undefined
                    }
                  />
                ))}
                <div ref={traceEndRef} />
              </div>
            )}

            {/* Artifacts button */}
            {artifacts && artifacts.length > 0 && (
              <button
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border bg-muted/20 text-xs font-medium text-muted-foreground hover:bg-muted/30 transition-colors"
                onClick={() => setArtifactsOpen(true)}
              >
                <Package className="h-3.5 w-3.5" />
                Artifacts ({artifacts.length})
                <ChevronRight className="h-3.5 w-3.5 ml-auto" />
              </button>
            )}
          </>
        )}
      </div>

      {/* Artifacts sidebar */}
      <Sheet open={artifactsOpen} onOpenChange={setArtifactsOpen}>
        <SheetContent className="w-full sm:w-[480px] sm:max-w-[480px] p-0 flex flex-col">
          <SheetHeader className="px-4 py-3 border-b shrink-0">
            <SheetTitle className="text-sm">Artifacts</SheetTitle>
          </SheetHeader>
          {artifacts && artifacts.length > 0 && (
            <ArtifactDrawerContent
              artifacts={artifacts}
              sessionId={sessionId}
            />
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

import { useMemo } from "react";
import { buildStagesList, buildTaskTree } from "@/lib/session-utils";
import type { StageInfo } from "@/lib/session-utils";
import type { TaskTreeNode } from "@/lib/session-utils";
import type { TraceEvent } from "@/hooks/use-session-trace";
import {
  mergeStagesAndTrace,
  deriveNodeExecutionStates,
} from "@/lib/session-constants";
import type { UnifiedNode } from "@/lib/session-constants";
import type { NodeExecutionState } from "@/components/WorkflowPipeline";
import type {
  WorkflowSession,
  NodeInstance,
  BatonHistoryEntry,
  ContextAuditEntry,
  WorkflowDetail,
} from "@/types/api";

export interface SessionComputed {
  stages: StageInfo[];
  taskTree: TaskTreeNode[];
  currentStage: StageInfo | undefined;
  pendingGates: Array<{
    nodeId: string;
    nodeInstance: NodeInstance | undefined;
  }>;
  failedNodes: Array<{
    nodeId: string;
    errorMessage: string | undefined;
    failureKind: string | undefined;
  }>;
  blockedNodes: Array<{
    nodeId: string;
    blockedReason: string | undefined;
  }>;
  unifiedNodes: UnifiedNode[];
  nodeExecutionStates: Record<string, NodeExecutionState>;
  structuredOutputs: Record<string, any>;
  batonHistoryByStage: Map<string, BatonHistoryEntry>;
  contextAuditByStage: Map<string, ContextAuditEntry>;
  isStalled: boolean;
  isOrphaned: boolean;
  isFailed: boolean;
  runtime: string | null;
  completedCount: number;
  failedCount: number;
  runningCount: number;
  waitingCount: number;
  progressPct: number;
  featureTitle: string | undefined;
  workflowSnapshot: WorkflowDetail | undefined;
  hasDAG: boolean;
  totalUsage: { cost: number; tokensIn: number; tokensOut: number };
}

export function useSessionComputed(
  session: WorkflowSession | undefined,
  events: TraceEvent[],
  executionFeature: { title?: string } | undefined,
): SessionComputed {
  const stages = useMemo(
    () => buildStagesList(session?.node_instances),
    [session?.node_instances],
  );

  const taskTree = useMemo(() => buildTaskTree(events), [events]);

  const currentStage = stages.find((s) => s.state === "running");

  const pendingGates = useMemo(
    () =>
      stages
        .filter((s) => s.state === "waiting")
        .map((s) => ({
          nodeId: s.nodeId,
          nodeInstance: session?.node_instances?.[s.nodeId],
        })),
    [stages, session?.node_instances],
  );

  const failedNodes = useMemo(
    () =>
      stages
        .filter((s) => s.state === "failed")
        .map((s) => ({
          nodeId: s.nodeId,
          errorMessage:
            session?.node_instances?.[s.nodeId]?.error_message ?? undefined,
          failureKind:
            session?.node_instances?.[s.nodeId]?.failure_kind ?? undefined,
        })),
    [stages, session?.node_instances],
  );

  const blockedNodes = useMemo(
    () =>
      stages
        .filter((s) => {
          const inst = session?.node_instances?.[s.nodeId];
          return (inst as any)?.state === "task_blocked";
        })
        .map((s) => ({
          nodeId: s.nodeId,
          blockedReason: (session?.node_instances?.[s.nodeId] as any)
            ?.blocked_reason as string | undefined,
        })),
    [stages, session?.node_instances],
  );

  const unifiedNodes = useMemo(
    () => mergeStagesAndTrace(stages, taskTree, session?.node_instances),
    [stages, taskTree, session?.node_instances],
  );

  const nodeExecutionStates = useMemo(
    () => deriveNodeExecutionStates(stages),
    [stages],
  );

  const structuredOutputs = session?.structured_outputs ?? {};

  const batonHistoryByStage = useMemo(() => {
    const map = new Map<string, BatonHistoryEntry>();
    for (const entry of session?.baton_history ?? []) {
      map.set(entry.stage_id, entry);
    }
    return map;
  }, [session?.baton_history]);

  const contextAuditByStage = useMemo(() => {
    const map = new Map<string, ContextAuditEntry>();
    for (const entry of session?.context_audit ?? []) {
      map.set(entry.stage_id, entry);
    }
    return map;
  }, [session?.context_audit]);

  const isStalled = session?.status === "stalled";
  const isOrphaned =
    session?.status === "running" && session?.is_orphaned === true;
  const isFailed = session?.status === "failed";

  const runtime = useMemo(() => {
    const totalSeconds = (session as any)?.execution_seconds;
    if (totalSeconds == null || totalSeconds === 0) return null;
    if (totalSeconds < 60) return `${Math.floor(totalSeconds)}s`;
    const minutes = Math.floor(totalSeconds / 60);
    const remainingSeconds = Math.floor(totalSeconds % 60);
    if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
  }, [session]);

  const completedCount = stages.filter((s) => s.state === "completed").length;
  const failedCount = stages.filter((s) => s.state === "failed").length;
  const runningCount = stages.filter((s) => s.state === "running").length;
  const waitingCount = pendingGates.length;
  const progressPct =
    stages.length > 0 ? Math.round((completedCount / stages.length) * 100) : 0;

  const featureTitle = executionFeature?.title || session?.feature_id;

  const workflowSnapshot = (session as any)?.workflow_snapshot as
    | WorkflowDetail
    | undefined;
  const hasDAG =
    !!workflowSnapshot &&
    !!workflowSnapshot.nodes &&
    Object.keys(workflowSnapshot.nodes).length > 0;

  const totalUsage = useMemo(() => {
    let cost = 0;
    let tokensIn = 0;
    let tokensOut = 0;
    for (const node of unifiedNodes) {
      const instAny = node.nodeInstance as unknown as
        | Record<string, unknown>
        | undefined;
      if (instAny?.cost_usd && typeof instAny.cost_usd === "number") {
        cost += instAny.cost_usd;
      }
      if (instAny?.input_tokens && typeof instAny.input_tokens === "number") {
        tokensIn += instAny.input_tokens;
      }
      if (instAny?.output_tokens && typeof instAny.output_tokens === "number") {
        tokensOut += instAny.output_tokens;
      }
    }
    return { cost, tokensIn, tokensOut };
  }, [unifiedNodes]);

  return {
    stages,
    taskTree,
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
  };
}

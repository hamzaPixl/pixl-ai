import type { UnifiedNode } from "@/lib/session-constants";
import type { ContextAuditEntry } from "@/types/api";

export interface NodeStats {
  modelName: string | undefined;
  agentName: string | undefined;
  duration: number | undefined;
  eventCount: number;
  inputTokens: number | undefined;
  outputTokens: number | undefined;
  costUsd: number | undefined;
  ctxPct: number | null;
  ctxColor: string;
}

export function computeNodeStats(
  node: UnifiedNode,
  contextAudit?: ContextAuditEntry,
): NodeStats {
  const inst = node.nodeInstance;
  const task = node.taskNode;
  const modelName = inst?.model_name || task?.effectiveModel;
  const agentName = inst?.agent_name || task?.agentName;
  const duration =
    task?.durationSeconds ??
    (inst?.started_at && inst?.ended_at
      ? (new Date(inst.ended_at).getTime() -
          new Date(inst.started_at).getTime()) /
        1000
      : undefined);
  const eventCount = task?.children.length ?? 0;
  const instAny = inst as unknown as Record<string, unknown> | undefined;
  const inputTokens = instAny?.input_tokens as number | undefined;
  const outputTokens = instAny?.output_tokens as number | undefined;
  const costUsd = instAny?.cost_usd as number | undefined;

  const ctxPct = contextAudit
    ? Math.round(contextAudit.utilization * 100)
    : null;
  const ctxColor =
    ctxPct !== null
      ? ctxPct > 95
        ? "text-red-500"
        : ctxPct > 80
          ? "text-yellow-500"
          : "text-green-500"
      : "";

  return {
    modelName,
    agentName,
    duration,
    eventCount,
    inputTokens,
    outputTokens,
    costUsd,
    ctxPct,
    ctxColor,
  };
}

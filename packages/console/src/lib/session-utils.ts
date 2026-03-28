/**
 * Session utility types and builder functions.
 *
 * Transforms raw backend types (NodeInstance, TraceEvent) into
 * presentation-friendly structures for session detail components.
 */

import type { NodeInstance, NodeState } from "@/types/api";
import type { TraceEvent } from "@/hooks/use-session-trace";

// Types

export type StageState =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "waiting"
  | "skipped";

export interface StageInfo {
  nodeId: string;
  state: StageState;
  attempt: number;
}

export type EventLifecycle = "started" | "running" | "completed" | "failed";

export type TraceEventNode =
  | ToolTraceNode
  | ThinkingTraceNode
  | TextTraceNode
  | ErrorTraceNode
  | QueryTraceNode
  | GateTraceNode
  | RecoveryTraceNode
  | ContractTraceNode;

export interface ToolTraceNode {
  kind: "tool";
  id: string;
  timestamp: Date;
  lifecycle: EventLifecycle;
  toolName: string;
  toolInput?: Record<string, unknown>;
  duration?: number;
  isError?: boolean;
  errorMessage?: string;
}

export interface ThinkingTraceNode {
  kind: "thinking";
  id: string;
  timestamp: Date;
  lifecycle: EventLifecycle;
  text?: string;
}

export interface TextTraceNode {
  kind: "text";
  id: string;
  timestamp: Date;
  text?: string;
}

export interface ErrorTraceNode {
  kind: "error";
  id: string;
  timestamp: Date;
  error?: string;
  errorType?: string;
}

export interface QueryTraceNode {
  kind: "query";
  id: string;
  timestamp: Date;
  lifecycle: EventLifecycle;
  model?: string;
  totalTokens?: number;
  durationSeconds?: number;
  numTurns?: number;
  promptPreview?: string;
}

export interface GateTraceNode {
  kind: "gate";
  id: string;
  timestamp: Date;
  gateAction: "requested" | "approved" | "rejected" | "timeout";
  artifacts?: string[];
  approver?: string;
  reason?: string;
}

export interface RecoveryTraceNode {
  kind: "recovery";
  id: string;
  timestamp: Date;
  recoveryAction:
    | "requested"
    | "decision"
    | "succeeded"
    | "failed"
    | "escalated";
  action?: string;
  errorType?: string;
  attempt?: number;
  decisionReason?: string;
}

export interface ContractTraceNode {
  kind: "contract";
  id: string;
  timestamp: Date;
  contractAction: "passed" | "violation" | "warning";
  violations?: string[];
  warning?: string;
  check?: string;
}

export interface TaskTreeNode {
  nodeId: string;
  status: "pending" | "running" | "completed" | "failed";
  children: TraceEventNode[];
  effectiveModel?: string;
  agentName?: string;
  durationSeconds?: number;
  errorMessage?: string;
}

// Helpers

const NODE_STATE_MAP: Record<NodeState, StageState> = {
  // Task states
  task_pending: "pending",
  task_running: "running",
  task_paused: "pending",
  task_completed: "completed",
  task_failed: "failed",
  task_blocked: "pending",
  task_skipped: "skipped",
  // Gate states
  gate_pending: "pending",
  gate_waiting: "waiting",
  gate_approved: "completed",
  gate_rejected: "failed",
  gate_timeout: "failed",
  // Parallel/Merge states
  parallel_waiting: "waiting",
  parallel_ready: "running",
  merge_waiting: "waiting",
};

function traceEventKind(eventType: string): TraceEventNode["kind"] | null {
  if (eventType.startsWith("sdk_tool_call")) return "tool";
  if (eventType.startsWith("sdk_thinking")) return "thinking";
  if (eventType === "sdk_text_delta") return "text";
  if (eventType === "sdk_error") return "error";
  if (eventType.startsWith("sdk_query")) return "query";
  if (eventType.startsWith("gate_")) return "gate";
  if (eventType.startsWith("recovery_")) return "recovery";
  if (eventType.startsWith("contract_") || eventType === "git_unavailable")
    return "contract";
  return null;
}

// Builders

/**
 * Convert session node_instances map into an ordered list of StageInfo.
 * Ordered by ready_at / started_at timestamp, falling back to key order.
 */
export function buildStagesList(
  nodeInstances?: Record<string, NodeInstance>,
): StageInfo[] {
  if (!nodeInstances) return [];

  return Object.entries(nodeInstances)
    .sort(([, a], [, b]) => {
      const ta = a.ready_at || a.started_at || "";
      const tb = b.ready_at || b.started_at || "";
      return ta.localeCompare(tb);
    })
    .map(([nodeId, inst]) => ({
      nodeId,
      state: NODE_STATE_MAP[inst.state] ?? "pending",
      attempt: inst.attempt,
    }));
}

/**
 * Build a hierarchical task tree from flat trace events.
 *
 * Task-level events (task_started, task_completed, …) create top-level nodes.
 * SDK-level events that share the same node_id are nested as children.
 */
export function buildTaskTree(events: TraceEvent[]): TaskTreeNode[] {
  const taskMap = new Map<string, TaskTreeNode>();
  const order: string[] = [];
  const pendingTools = new Map<
    string,
    {
      id: string;
      timestamp: Date;
      toolName: string;
      toolInput?: Record<string, unknown>;
    }
  >();
  const pendingThinking = new Map<string, { id: string; timestamp: Date }>();
  const pendingQueries = new Map<
    string,
    { id: string; timestamp: Date; model?: string; promptPreview?: string }
  >();

  function ensureNode(nodeId: string): TaskTreeNode {
    let node = taskMap.get(nodeId);
    if (!node) {
      node = { nodeId, status: "running", children: [] };
      taskMap.set(nodeId, node);
      order.push(nodeId);
    }
    return node;
  }

  for (const evt of events) {
    const raw = evt as unknown as Record<string, unknown>;
    const nodeId = raw.node_id as string | undefined;
    if (!nodeId) continue;

    const eventType = raw.event_type as string;

    if (eventType.startsWith("task_")) {
      const node = ensureNode(nodeId);
      if (eventType === "task_started") {
        node.status = "running";
        if (raw.model) node.effectiveModel = raw.model as string;
        if (raw.agent_name) node.agentName = raw.agent_name as string;
      } else if (eventType === "task_completed") {
        node.status = "completed";
        if (typeof raw.duration_seconds === "number")
          node.durationSeconds = raw.duration_seconds;
      } else if (eventType === "task_failed") {
        node.status = "failed";
        node.errorMessage =
          (raw.error as string) || (raw.error_message as string) || undefined;
        if (typeof raw.duration_seconds === "number")
          node.durationSeconds = raw.duration_seconds;
      }
      continue;
    }

    const kind = traceEventKind(eventType);
    if (!kind) continue;

    const node = ensureNode(nodeId);
    const ts = evt.timestamp;

    if (kind === "tool") {
      if (eventType === "sdk_tool_call_started") {
        const toolName = (raw.tool_name as string) || "Unknown";
        const key = `${nodeId}:${toolName}`;
        // Close any previous running tool with the same key
        const prevPendingTool = pendingTools.get(key);
        if (prevPendingTool) {
          const idx = node.children.findIndex(
            (c) => c.kind === "tool" && c.id === prevPendingTool.id,
          );
          if (
            idx >= 0 &&
            "lifecycle" in node.children[idx] &&
            (node.children[idx] as ToolTraceNode).lifecycle === "running"
          ) {
            const duration =
              (ts.getTime() - prevPendingTool.timestamp.getTime()) / 1000;
            node.children[idx] = {
              ...(node.children[idx] as ToolTraceNode),
              lifecycle: "completed" as const,
              duration,
            };
          }
        }
        pendingTools.set(key, {
          id: evt.id,
          timestamp: ts,
          toolName,
          toolInput: raw.tool_input as Record<string, unknown> | undefined,
        });
        node.children.push({
          kind: "tool",
          id: evt.id,
          timestamp: ts,
          lifecycle: "running",
          toolName,
          toolInput: raw.tool_input as Record<string, unknown> | undefined,
        });
      } else if (eventType === "sdk_tool_call_completed") {
        const toolName = (raw.tool_name as string) || "Unknown";
        const key = `${nodeId}:${toolName}`;
        const pending = pendingTools.get(key);
        if (pending) {
          const idx = node.children.findIndex(
            (c) => c.kind === "tool" && c.id === pending.id,
          );
          if (idx >= 0) {
            const duration =
              (ts.getTime() - pending.timestamp.getTime()) / 1000;
            node.children[idx] = {
              kind: "tool",
              id: pending.id,
              timestamp: pending.timestamp,
              lifecycle: (raw.is_error as boolean) ? "failed" : "completed",
              toolName,
              toolInput: pending.toolInput,
              duration,
              isError: (raw.is_error as boolean) || undefined,
              errorMessage: (raw.error_message as string) || undefined,
            };
          }
          pendingTools.delete(key);
        } else {
          node.children.push({
            kind: "tool",
            id: evt.id,
            timestamp: ts,
            lifecycle: (raw.is_error as boolean) ? "failed" : "completed",
            toolName,
            toolInput: raw.tool_input as Record<string, unknown> | undefined,
            isError: (raw.is_error as boolean) || undefined,
            errorMessage: (raw.error_message as string) || undefined,
          });
        }
      }
      continue;
    }

    if (kind === "thinking") {
      if (eventType === "sdk_thinking_started") {
        // Close any previous running thinking event for this node
        const prevPendingThinking = pendingThinking.get(nodeId);
        if (prevPendingThinking) {
          const idx = node.children.findIndex(
            (c) => c.kind === "thinking" && c.id === prevPendingThinking.id,
          );
          if (
            idx >= 0 &&
            "lifecycle" in node.children[idx] &&
            (node.children[idx] as ThinkingTraceNode).lifecycle === "running"
          ) {
            node.children[idx] = {
              ...(node.children[idx] as ThinkingTraceNode),
              lifecycle: "completed" as const,
            };
          }
        }
        pendingThinking.set(nodeId, { id: evt.id, timestamp: ts });
        node.children.push({
          kind: "thinking",
          id: evt.id,
          timestamp: ts,
          lifecycle: "running",
          text: (raw.thinking_preview as string) || undefined,
        });
      } else if (eventType === "sdk_thinking_completed") {
        const pending = pendingThinking.get(nodeId);
        if (pending) {
          const idx = node.children.findIndex(
            (c) => c.kind === "thinking" && c.id === pending.id,
          );
          if (idx >= 0) {
            node.children[idx] = {
              ...(node.children[idx] as ThinkingTraceNode),
              lifecycle: "completed",
              text:
                (raw.thinking_preview as string) ||
                (node.children[idx] as ThinkingTraceNode).text,
            };
          }
          pendingThinking.delete(nodeId);
        }
      }
      continue;
    }

    if (kind === "query") {
      if (eventType === "sdk_query_started") {
        // Close any previous running query event for this node
        const prevPendingQuery = pendingQueries.get(nodeId);
        if (prevPendingQuery) {
          const idx = node.children.findIndex(
            (c) => c.kind === "query" && c.id === prevPendingQuery.id,
          );
          if (
            idx >= 0 &&
            "lifecycle" in node.children[idx] &&
            (node.children[idx] as QueryTraceNode).lifecycle === "running"
          ) {
            node.children[idx] = {
              ...(node.children[idx] as QueryTraceNode),
              lifecycle: "completed" as const,
            };
          }
        }
        pendingQueries.set(nodeId, {
          id: evt.id,
          timestamp: ts,
          model: raw.model as string | undefined,
          promptPreview: raw.prompt_preview as string | undefined,
        });
        node.children.push({
          kind: "query",
          id: evt.id,
          timestamp: ts,
          lifecycle: "running",
          model: raw.model as string | undefined,
          promptPreview: raw.prompt_preview as string | undefined,
        });
      } else if (eventType === "sdk_query_completed") {
        const pending = pendingQueries.get(nodeId);
        if (pending) {
          const idx = node.children.findIndex(
            (c) => c.kind === "query" && c.id === pending.id,
          );
          if (idx >= 0) {
            node.children[idx] = {
              kind: "query",
              id: pending.id,
              timestamp: pending.timestamp,
              lifecycle: "completed",
              model: (raw.model as string) || pending.model,
              totalTokens: raw.total_tokens as number | undefined,
              durationSeconds: raw.duration_seconds as number | undefined,
              numTurns: raw.num_turns as number | undefined,
              promptPreview: pending.promptPreview,
            };
          }
          pendingQueries.delete(nodeId);
        } else {
          node.children.push({
            kind: "query",
            id: evt.id,
            timestamp: ts,
            lifecycle: "completed",
            model: raw.model as string | undefined,
            totalTokens: raw.total_tokens as number | undefined,
            durationSeconds: raw.duration_seconds as number | undefined,
            numTurns: raw.num_turns as number | undefined,
          });
        }
      }
      continue;
    }

    if (kind === "text") {
      node.children.push({
        kind: "text",
        id: evt.id,
        timestamp: ts,
        text: (raw.text as string) || undefined,
      });
      continue;
    }

    if (kind === "error") {
      node.children.push({
        kind: "error",
        id: evt.id,
        timestamp: ts,
        error: (raw.error as string) || undefined,
        errorType: (raw.error_type as string) || undefined,
      });
      continue;
    }

    if (kind === "gate") {
      const actionMap: Record<string, GateTraceNode["gateAction"]> = {
        gate_requested: "requested",
        gate_approved: "approved",
        gate_rejected: "rejected",
        gate_timeout: "timeout",
      };
      node.children.push({
        kind: "gate",
        id: evt.id,
        timestamp: ts,
        gateAction: actionMap[eventType] || "requested",
        artifacts: raw.artifacts as string[] | undefined,
        approver: raw.approver as string | undefined,
        reason: raw.reason as string | undefined,
      });
      continue;
    }

    if (kind === "recovery") {
      const actionMap: Record<string, RecoveryTraceNode["recoveryAction"]> = {
        recovery_requested: "requested",
        recovery_decision: "decision",
        recovery_succeeded: "succeeded",
        recovery_failed: "failed",
        recovery_escalated: "escalated",
      };
      node.children.push({
        kind: "recovery",
        id: evt.id,
        timestamp: ts,
        recoveryAction: actionMap[eventType] || "requested",
        action: raw.action as string | undefined,
        errorType: raw.error_type as string | undefined,
        attempt: raw.attempt as number | undefined,
        decisionReason: raw.decision_reason as string | undefined,
      });
      continue;
    }

    if (kind === "contract") {
      const actionMap: Record<string, ContractTraceNode["contractAction"]> = {
        contract_passed: "passed",
        contract_violation: "violation",
        contract_warning: "warning",
        git_unavailable: "warning",
      };
      node.children.push({
        kind: "contract",
        id: evt.id,
        timestamp: ts,
        contractAction: actionMap[eventType] || "warning",
        violations: raw.violations as string[] | undefined,
        warning:
          (raw.warning as string) ||
          (eventType === "git_unavailable" ? "Git unavailable" : undefined),
        check: raw.check as string | undefined,
      });
      continue;
    }
  }

  // Resolve any still-running children when the parent task is terminal.
  // This handles unpaired started events (e.g. tool_call_started without
  // a matching _completed) and unresolved gate/recovery events that would
  // otherwise flash indefinitely after the workflow ends.
  for (const node of taskMap.values()) {
    if (node.status !== "completed" && node.status !== "failed") continue;
    const resolvedLifecycle: EventLifecycle =
      node.status === "failed" ? "failed" : "completed";
    for (let i = 0; i < node.children.length; i++) {
      const child = node.children[i];
      if (
        "lifecycle" in child &&
        (child.lifecycle === "running" || child.lifecycle === "started")
      ) {
        node.children[i] = { ...child, lifecycle: resolvedLifecycle };
      }
      // Resolve unfinished gate events
      if (child.kind === "gate" && child.gateAction === "requested") {
        node.children[i] = {
          ...child,
          gateAction: node.status === "failed" ? "timeout" : "approved",
        };
      }
      // Resolve unfinished recovery events
      if (
        child.kind === "recovery" &&
        (child.recoveryAction === "requested" ||
          child.recoveryAction === "decision")
      ) {
        node.children[i] = {
          ...child,
          recoveryAction: node.status === "failed" ? "failed" : "succeeded",
        };
      }
    }
  }

  return order.map((id) => taskMap.get(id)!);
}

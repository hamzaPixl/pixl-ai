import React from "react";
import type { StageInfo, TaskTreeNode } from "@/lib/session-utils";
import type { NodeInstance } from "@/types/api";
import type { NodeExecutionState } from "@/components/WorkflowPipeline";
import {
  Clock,
  Play,
  CheckCircle2,
  XCircle,
  ShieldQuestion,
  ChevronRight,
} from "lucide-react";

export interface UnifiedNode {
  nodeId: string;
  state: StageInfo["state"];
  attempt: number;
  nodeInstance?: NodeInstance;
  taskNode?: TaskTreeNode;
}

export type PanelMode =
  | { mode: "overview" }
  | { mode: "node"; nodeId: string }
  | { mode: "artifact"; artifactId?: string };

export function mergeStagesAndTrace(
  stages: StageInfo[],
  taskTree: TaskTreeNode[],
  nodeInstances?: Record<string, NodeInstance>,
): UnifiedNode[] {
  const taskMap = new Map(taskTree.map((t) => [t.nodeId, t]));
  const seen = new Set<string>();
  const result: UnifiedNode[] = [];

  for (const stage of stages) {
    seen.add(stage.nodeId);
    result.push({
      nodeId: stage.nodeId,
      state: stage.state,
      attempt: stage.attempt,
      nodeInstance: nodeInstances?.[stage.nodeId],
      taskNode: taskMap.get(stage.nodeId),
    });
  }

  for (const task of taskTree) {
    if (!seen.has(task.nodeId)) {
      result.push({
        nodeId: task.nodeId,
        state: "running",
        attempt: 1,
        taskNode: task,
      });
    }
  }

  return result;
}

export const STATE_ICONS: Record<StageInfo["state"], React.ReactNode> = {
  pending: <Clock className="h-4 w-4 text-muted-foreground" />,
  running: <Play className="h-4 w-4 text-blue-500" />,
  completed: <CheckCircle2 className="h-4 w-4 text-green-500" />,
  failed: <XCircle className="h-4 w-4 text-red-500" />,
  waiting: <ShieldQuestion className="h-4 w-4 text-yellow-500" />,
  skipped: <ChevronRight className="h-4 w-4 text-muted-foreground" />,
};

export function deriveNodeExecutionStates(
  stages: StageInfo[],
): Record<string, NodeExecutionState> {
  const states: Record<string, NodeExecutionState> = {};
  for (const stage of stages) {
    states[stage.nodeId] = {
      state: stage.state,
      attempt: stage.attempt,
    };
  }
  return states;
}

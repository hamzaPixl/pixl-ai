export interface WorkflowRoutingHints {
  auto_route: boolean;
  sub_invocable: boolean;
  category: string;
  trigger_keywords: string[];
}

export interface WorkflowSummary {
  id: string;
  name: string;
  description?: string;
  version?: string;
  tags?: string[];
  source?: string;
  tier?: string;
  routing?: WorkflowRoutingHints;
  [key: string]: unknown;
}

export interface WorkflowNodeDetail {
  id: string;
  type: "task" | "gate" | "hook" | "parallel" | "merge" | "sub_workflow";
  task_config: {
    agent: string;
    max_turns: number;
    retry_policy?: unknown;
  } | null;
  gate_config: {
    id: string;
    name: string;
    description: string;
    timeout_minutes: number | null;
    timeout_policy: string;
  } | null;
  hook_config: { hook: string } | null;
  metadata?: Record<string, string>;
}

export interface WorkflowEdgeDetail {
  to: string;
  on: string;
  condition: string | null;
}

export interface WorkflowLoopDetail {
  id: string;
  from_node: string;
  to_node: string;
  max_iterations: number;
  edge_trigger: string;
}

export interface WorkflowDetail {
  id: string;
  name: string;
  description: string;
  tags: string[];
  version: string;
  tier?: string;
  routing?: WorkflowRoutingHints;
  nodes: Record<string, WorkflowNodeDetail>;
  edges: Record<string, WorkflowEdgeDetail[]>;
  loops: WorkflowLoopDetail[];
  stages: unknown[];
  variables: Record<string, string>;
}

import type { AgentInfo } from "@/types/api";

export type RoleKey =
  | "strategy"
  | "implementation"
  | "testing"
  | "review"
  | "operations";

export const ROLE_META: Record<
  RoleKey,
  {
    label: string;
    description: string;
    fill: string;
    stroke: string;
    bg: string;
    bgActive: string;
    text: string;
    dot: string;
    border: string;
  }
> = {
  strategy: {
    label: "Strategy",
    description: "Planning, architecture & analysis",
    fill: "#8b5cf6",
    stroke: "#7c3aed",
    bg: "bg-violet-500/5",
    bgActive: "bg-violet-500/10",
    text: "text-violet-600 dark:text-violet-400",
    dot: "bg-violet-500",
    border: "border-violet-500/20",
  },
  implementation: {
    label: "Implementation",
    description: "Code generation & building",
    fill: "#3b82f6",
    stroke: "#2563eb",
    bg: "bg-blue-500/5",
    bgActive: "bg-blue-500/10",
    text: "text-blue-600 dark:text-blue-400",
    dot: "bg-blue-500",
    border: "border-blue-500/20",
  },
  testing: {
    label: "Testing",
    description: "Tests, debugging & validation",
    fill: "#10b981",
    stroke: "#059669",
    bg: "bg-emerald-500/5",
    bgActive: "bg-emerald-500/10",
    text: "text-emerald-600 dark:text-emerald-400",
    dot: "bg-emerald-500",
    border: "border-emerald-500/20",
  },
  review: {
    label: "Review",
    description: "Code & plan review, security audit",
    fill: "#f59e0b",
    stroke: "#d97706",
    bg: "bg-amber-500/5",
    bgActive: "bg-amber-500/10",
    text: "text-amber-600 dark:text-amber-400",
    dot: "bg-amber-500",
    border: "border-amber-500/20",
  },
  operations: {
    label: "Operations",
    description: "Exploration, docs & tooling",
    fill: "#ec4899",
    stroke: "#db2777",
    bg: "bg-pink-500/5",
    bgActive: "bg-pink-500/10",
    text: "text-pink-600 dark:text-pink-400",
    dot: "bg-pink-500",
    border: "border-pink-500/20",
  },
};

export const ROLE_ORDER: RoleKey[] = [
  "strategy",
  "implementation",
  "testing",
  "review",
  "operations",
];

export const AGENT_ROLE_MAP: Record<string, RoleKey> = {
  planner: "strategy",
  architect: "strategy",
  oracle: "strategy",
  implementer: "implementation",
  "frontend-implementer": "implementation",
  "build-fixer": "implementation",
  "test-writer": "testing",
  "e2e-runner": "testing",
  debugger: "testing",
  "frontend-debugger": "testing",
  reviewer: "review",
  "code-reviewer": "review",
  "plan-reviewer": "review",
  "security-reviewer": "review",
  judge: "review",
  explorer: "operations",
  "doc-generator": "operations",
  "git-sync": "operations",
  librarian: "operations",
  multimodal: "operations",
};

export function deriveRole(agent: AgentInfo): RoleKey {
  const mapped = AGENT_ROLE_MAP[agent.name];
  if (mapped) return mapped;
  const hay = `${agent.name} ${agent.description}`.toLowerCase();
  if (
    hay.includes("plan") ||
    hay.includes("architect") ||
    hay.includes("strateg")
  )
    return "strategy";
  if (
    hay.includes("review") ||
    hay.includes("audit") ||
    hay.includes("security")
  )
    return "review";
  if (hay.includes("test") || hay.includes("debug") || hay.includes("e2e"))
    return "testing";
  if (
    hay.includes("implement") ||
    hay.includes("build") ||
    hay.includes("code") ||
    hay.includes("frontend")
  )
    return "implementation";
  return "operations";
}

export type TierKey = "opus" | "sonnet" | "codex" | "haiku";

export const TIER_META: Record<
  TierKey,
  { label: string; color: string; bg: string; text: string }
> = {
  opus: {
    label: "Opus",
    color: "#a78bfa",
    bg: "bg-violet-100 dark:bg-violet-900/30",
    text: "text-violet-700 dark:text-violet-300",
  },
  sonnet: {
    label: "Sonnet",
    color: "#60a5fa",
    bg: "bg-blue-100 dark:bg-blue-900/30",
    text: "text-blue-700 dark:text-blue-300",
  },
  codex: {
    label: "Codex",
    color: "#fbbf24",
    bg: "bg-amber-100 dark:bg-amber-900/30",
    text: "text-amber-700 dark:text-amber-300",
  },
  haiku: {
    label: "Haiku",
    color: "#34d399",
    bg: "bg-emerald-100 dark:bg-emerald-900/30",
    text: "text-emerald-700 dark:text-emerald-300",
  },
};

export function deriveTier(model: string): TierKey {
  if (model.includes("opus")) return "opus";
  if (model.includes("codex") || model.includes("gpt")) return "codex";
  if (model.includes("haiku")) return "haiku";
  return "sonnet";
}

export function stripProvider(model: string): string {
  const idx = model.indexOf("/");
  return idx >= 0 ? model.slice(idx + 1) : model;
}

export const WORKFLOW_EDGES: Array<[source: string, target: string]> = [
  ["explorer", "oracle"],
  ["oracle", "planner"],
  ["planner", "plan-reviewer"],
  ["plan-reviewer", "planner"],
  ["test-writer", "implementer"],
  ["planner", "implementer"],
  ["implementer", "e2e-runner"],
  ["e2e-runner", "reviewer"],
  ["implementer", "reviewer"],
  ["reviewer", "code-reviewer"],
  ["code-reviewer", "implementer"],
  ["code-reviewer", "build-fixer"],
  ["build-fixer", "oracle"],
  ["oracle", "git-sync"],
  ["explorer", "debugger"],
  ["debugger", "implementer"],
];

export function getAgentConnections(agentName: string) {
  const downstream: string[] = [];
  const upstream: string[] = [];
  const loops: Array<{ with: string; direction: "to" | "from" }> = [];

  for (const [s, t] of WORKFLOW_EDGES) {
    if (s === agentName && t === agentName) continue;
    if (s === agentName) {
      const isLoop = WORKFLOW_EDGES.some(
        ([rs, rt]) => rs === t && rt === agentName,
      );
      if (isLoop) {
        if (!loops.find((l) => l.with === t)) {
          loops.push({ with: t, direction: "to" });
        }
      } else {
        downstream.push(t);
      }
    }
    if (t === agentName) {
      const isLoop = WORKFLOW_EDGES.some(
        ([rs, rt]) => rs === agentName && rt === s,
      );
      if (isLoop) {
        if (!loops.find((l) => l.with === s)) {
          loops.push({ with: s, direction: "from" });
        }
      } else {
        upstream.push(s);
      }
    }
  }

  return { upstream, downstream, loops };
}

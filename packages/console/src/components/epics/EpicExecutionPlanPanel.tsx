import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { StatusBadge } from "@/components/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  GitBranch,
  Play,
  Pause,
  XCircle,
  Loader2,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { RISK_BADGE_CLASS } from "@/lib/epic-constants";
import { SwarmActivityPanel } from "./SwarmActivityPanel";
import type { EpicExecutionPlan } from "@/types/api";

async function fetchEpicExecutionPlan(
  projectId: string,
  epicId: string,
): Promise<EpicExecutionPlan | null> {
  const response = await fetch(
    `/api/projects/${projectId}/views/epics/${epicId}/plan`,
  );
  if (response.status === 404) return null;
  if (!response.ok) {
    let message = `Failed to load execution plan (${response.status})`;
    try {
      const payload = await response.json();
      if (payload?.error) message = String(payload.error);
    } catch {
      // no-op
    }
    throw new Error(message);
  }
  return response.json();
}

export interface EpicExecutionPlanPanelProps {
  epicId: string;
  projectId: string;
}

export function EpicExecutionPlanPanel({
  epicId,
  projectId,
}: EpicExecutionPlanPanelProps) {
  const [actionPending, setActionPending] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const {
    data: plan,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["views", "epic-plan", projectId, epicId],
    queryFn: () => fetchEpicExecutionPlan(projectId, epicId),
    enabled: !!projectId && !!epicId,
    refetchInterval: (query) => {
      const status = (query.state.data as any)?.status;
      if (status === "running") return 2000;
      if (status === "paused") return 5000;
      return false;
    },
  });

  const runChainAction = async (
    action: "start" | "pause" | "resume" | "cancel" | "reset",
  ): Promise<boolean> => {
    if (!plan) return false;
    setActionPending(true);
    setActionError(null);
    try {
      const response = await fetch(
        `/api/projects/${projectId}/control/chains/${plan.chain_id}/${action}`,
        { method: "POST" },
      );
      if (!response.ok) {
        let message = `Failed to ${action} chain (${response.status})`;
        try {
          const payload = await response.json();
          if (payload?.error) message = String(payload.error);
        } catch {
          // no-op
        }
        setActionError(message);
        return false;
      }
      await refetch();
      return true;
    } finally {
      setActionPending(false);
    }
  };

  if (isLoading) {
    return (
      <div className="mt-3 rounded-lg border border-border/60 p-4 space-y-2">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mt-3 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
        {(error as Error).message}
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="mt-3 rounded-lg border border-dashed border-border p-3 text-xs text-muted-foreground">
        Execution plan not materialized yet.
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-lg border border-border/60 bg-muted/20 p-4 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-muted-foreground" />
            <h4 className="font-medium">Execution Plan</h4>
            <StatusBadge status={plan.status as any} />
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {plan.chain_id} · {plan.edges.length} dependency edge
            {plan.edges.length !== 1 ? "s" : ""} · max parallel{" "}
            {plan.execution_policy.max_parallel}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {plan.status === "plan_ready" && (
            <Button
              size="sm"
              onClick={() => runChainAction("start")}
              disabled={actionPending}
            >
              {actionPending ? (
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              ) : (
                <Play className="h-3 w-3 mr-1" />
              )}
              Start
            </Button>
          )}
          {plan.status === "running" && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => runChainAction("pause")}
              disabled={actionPending}
            >
              <Pause className="h-3 w-3 mr-1" />
              Pause
            </Button>
          )}
          {plan.status === "paused" && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => runChainAction("resume")}
              disabled={actionPending}
            >
              <Play className="h-3 w-3 mr-1" />
              Resume
            </Button>
          )}
          {plan.status !== "completed" &&
            plan.status !== "failed" &&
            plan.status !== "cancelled" && (
              <Button
                size="sm"
                variant="destructive"
                onClick={() => runChainAction("cancel")}
                disabled={actionPending}
              >
                <XCircle className="h-3 w-3 mr-1" />
                Cancel
              </Button>
            )}
          {(plan.status === "failed" || plan.status === "cancelled") && (
            <Button
              size="sm"
              onClick={async () => {
                const resetOk = await runChainAction("reset");
                if (!resetOk) return;
                await refetch();
                await runChainAction("start");
              }}
              disabled={actionPending}
            >
              {actionPending ? (
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              ) : (
                <Play className="h-3 w-3 mr-1" />
              )}
              Retry
            </Button>
          )}
        </div>
      </div>

      {actionError && <p className="text-xs text-destructive">{actionError}</p>}

      <div className="grid gap-3 xl:grid-cols-2">
        <div className="rounded-md border border-border/60 bg-background p-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Readiness Checks
          </p>
          <div className="mt-2 space-y-1.5">
            {plan.readiness.checks.map((check) => (
              <div key={check.id} className="flex items-start gap-2 text-xs">
                {check.ok ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                ) : (
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
                )}
                <div className="min-w-0">
                  <p
                    className={
                      check.ok
                        ? "text-foreground"
                        : "text-amber-700 dark:text-amber-400"
                    }
                  >
                    {check.id.replace(/_/g, " ")}
                  </p>
                  <p className="text-muted-foreground">{check.detail}</p>
                </div>
              </div>
            ))}
          </div>
          {plan.readiness.blockers.length > 0 && (
            <div className="mt-3 rounded-md border border-amber-300/60 bg-amber-50/60 dark:bg-amber-950/20 p-2">
              <p className="text-[11px] font-medium text-amber-700 dark:text-amber-300">
                Blocked By
              </p>
              <ul className="mt-1 space-y-0.5 text-xs text-amber-700 dark:text-amber-300">
                {plan.readiness.blockers.map((blocker) => (
                  <li key={blocker}>{blocker}</li>
                ))}
              </ul>
            </div>
          )}
          {plan.readiness.dependency_issues.length > 0 && (
            <div className="mt-2 space-y-1">
              {plan.readiness.dependency_issues.map((issue, idx) => (
                <p
                  key={`${issue.from}-${issue.to}-${idx}`}
                  className="text-xs text-destructive"
                >
                  {issue.from} → {issue.to}: {issue.reason}
                </p>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-md border border-border/60 bg-background p-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Waves
          </p>
          {plan.waves.length === 0 ? (
            <p className="text-xs text-muted-foreground mt-2">No wave data.</p>
          ) : (
            <div className="mt-2 space-y-2">
              {plan.waves.map((wave) => (
                <div
                  key={wave.wave}
                  className="rounded border border-border/60 p-2"
                >
                  <p className="text-xs font-medium mb-1">
                    Wave {wave.wave + 1}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {wave.nodes.map((node) => (
                      <div
                        key={node.node_id}
                        className="inline-flex items-center gap-1.5 rounded-md border border-border px-2 py-1 text-[11px]"
                      >
                        <span
                          className={`inline-block w-2 h-2 rounded-full ${
                            node.status === "completed"
                              ? "bg-green-500"
                              : node.status === "running"
                                ? "bg-blue-500"
                                : node.status === "failed"
                                  ? "bg-red-500"
                                  : node.status === "blocked"
                                    ? "bg-amber-500"
                                    : node.status === "cancelled"
                                      ? "bg-muted-foreground/40"
                                      : node.status === "refined"
                                        ? "bg-purple-500"
                                        : "bg-muted-foreground/30"
                          }`}
                          title={node.status ?? "pending"}
                        />
                        <span>{node.feature_ref}</span>
                        {node.risk_class && (
                          <span
                            className={`rounded border px-1.5 py-0.5 ${RISK_BADGE_CLASS[node.risk_class] ?? "bg-muted text-foreground border-border"}`}
                          >
                            {node.risk_class}
                          </span>
                        )}
                        {node.estimate_points ? (
                          <span className="text-muted-foreground">
                            {node.estimate_points}pt
                          </span>
                        ) : null}
                        {node.status === "refined" && (
                          <span className="text-purple-500 text-[10px]">
                            refined
                          </span>
                        )}
                        {node.session_id ? (
                          <span className="text-muted-foreground/70 font-mono">
                            {String(node.session_id).slice(-8)}
                          </span>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Swarm: Signal Activity + Judge Verdicts */}
      {plan.chain_id &&
        (plan.status === "running" ||
          plan.status === "paused" ||
          plan.status === "completed" ||
          plan.status === "failed") && (
          <SwarmActivityPanel
            chainId={plan.chain_id}
            projectId={projectId}
            status={plan.status}
          />
        )}
    </div>
  );
}

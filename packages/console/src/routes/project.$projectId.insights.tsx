/**
 * Insights — single-page dashboard with inline cost, metrics, activity chart,
 * and a tabbed detail section for event log + artifacts.
 */

import { useState, useMemo } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";

import { ActivityChart } from "@/components/insights/ActivityChart";
import { ArtifactsTab } from "@/components/insights/ArtifactsTab";
import { KpiCard } from "@/components/insights/KpiCard";
import { useAgentMetrics } from "@/hooks/useMetrics";
import { usage } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { TIMEFRAMES } from "@/lib/insights-constants";
import { DollarSign, Zap, Coins, BarChart2, Clock } from "lucide-react";

export const Route = createFileRoute("/project/$projectId/insights")({
  component: InsightsPage,
});

function InsightsPage() {
  const { projectId } = Route.useParams();

  const [timeframeHours, setTimeframeHours] = useState<number | undefined>(168);

  // Data hooks
  const { data: metricsData } = useAgentMetrics(timeframeHours);
  const { data: usageData } = useQuery({
    queryKey: queryKeys.usage.summary(projectId),
    queryFn: () => usage.summary(),
    enabled: !!projectId,
  });

  // Derived data
  const agents = useMemo(
    () =>
      metricsData?.agents
        ? Object.values(metricsData.agents).sort(
            (a, b) => b.total_cost_usd - a.total_cost_usd,
          )
        : [],
    [metricsData],
  );

  const totalExecutions = agents.reduce((s, a) => s + a.total_executions, 0);
  const avgSuccessRate =
    agents.length > 0
      ? agents.reduce((s, a) => s + a.success_rate, 0) / agents.length
      : 0;

  const totals = usageData?.totals;
  const totalCost = totals?.cost_usd ?? 0;
  const totalTokens = totals?.total_tokens ?? 0;

  return (
    <div className="space-y-6">
      {/* Page header + timeframe */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold">Insights</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Cost, performance, and activity overview
          </p>
        </div>
        <Select
          value={String(timeframeHours ?? "all")}
          onValueChange={(v) =>
            setTimeframeHours(v === "all" ? undefined : Number(v))
          }
        >
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TIMEFRAMES.map((t) => (
              <SelectItem key={t.label} value={String(t.hours ?? "all")}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* ─── Top KPIs ────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-5">
        <KpiCard
          label="Total Cost"
          value={`$${totalCost.toFixed(2)}`}
          icon={<DollarSign className="h-4 w-4" />}
          sub={
            totals
              ? `${(totals.input_tokens ?? 0).toLocaleString()} in / ${(totals.output_tokens ?? 0).toLocaleString()} out`
              : undefined
          }
        />
        <KpiCard
          label="Total Tokens"
          value={totalTokens.toLocaleString()}
          icon={<Coins className="h-4 w-4" />}
        />
        {agents.length > 0 && (
          <>
            <KpiCard
              label="Executions"
              value={String(totalExecutions)}
              icon={<Zap className="h-4 w-4" />}
              sub={`across ${agents.length} agent${agents.length !== 1 ? "s" : ""}`}
            />
            <KpiCard
              label="Success Rate"
              value={`${(avgSuccessRate * 100).toFixed(0)}%`}
              icon={<BarChart2 className="h-4 w-4" />}
              sub={`across ${agents.length} agent${agents.length !== 1 ? "s" : ""}`}
            />
            <KpiCard
              label="Agents"
              value={String(agents.length)}
              icon={<Clock className="h-4 w-4" />}
              sub={`${totalExecutions} total runs`}
            />
          </>
        )}
      </div>

      {/* ─── Agent Performance ──────────────────────────── */}
      {agents.length > 0 && (
        <section className="space-y-4">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Agent Performance
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {agents.map((agent) => (
              <div
                key={agent.agent_name}
                className="space-y-3 rounded-lg border border-border p-4"
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium truncate">
                    {agent.agent_name}
                  </p>
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {agent.total_executions} runs
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Success</span>
                  <span className="tabular-nums">
                    {(agent.success_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <Progress value={agent.success_rate * 100} className="h-1.5" />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>${agent.total_cost_usd.toFixed(4)} total</span>
                  <span>{agent.avg_duration_seconds.toFixed(1)}s avg</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ─── Recent Activity ─────────────────────────── */}
      <section className="space-y-4">
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Recent Activity
        </h3>
        <ActivityChart />
      </section>

      {/* ─── Artifacts ───────────────────────────────── */}
      <section className="space-y-4">
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Artifacts
        </h3>
        <ArtifactsTab projectId={projectId} />
      </section>
    </div>
  );
}

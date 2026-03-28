/**
 * Agent Performance Metrics page.
 *
 * Shows agent performance grid with timeframe selector, comparison table,
 * and cost breakdown.
 */

import { createFileRoute, redirect } from "@tanstack/react-router";
import { useState } from "react";
import { useAgentMetrics } from "@/hooks/useMetrics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { BarChart2, Clock, DollarSign, Zap } from "lucide-react";

export const Route = createFileRoute("/project/$projectId/metrics")({
  beforeLoad: ({ params }) => {
    throw redirect({ to: "/project/$projectId/insights", params });
  },
  component: MetricsPage,
});

const TIMEFRAMES: { label: string; hours: number | undefined }[] = [
  { label: "24 hours", hours: 24 },
  { label: "7 days", hours: 168 },
  { label: "30 days", hours: 720 },
  { label: "All time", hours: undefined },
];

function MetricsPage() {
  Route.useParams(); // ensure route context
  const [timeframeHours, setTimeframeHours] = useState<number | undefined>(168);

  const { data, isLoading } = useAgentMetrics(timeframeHours);

  const agents = data?.agents
    ? Object.values(data.agents).sort(
        (a, b) => b.total_cost_usd - a.total_cost_usd,
      )
    : [];

  const totalCost = agents.reduce((sum, a) => sum + a.total_cost_usd, 0);
  const totalExecutions = agents.reduce(
    (sum, a) => sum + a.total_executions,
    0,
  );
  const avgSuccessRate =
    agents.length > 0
      ? agents.reduce((sum, a) => sum + a.success_rate, 0) / agents.length
      : 0;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Agent Metrics"
        description="Performance overview for all agents"
        action={
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
        }
      />

      {/* KPI Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Total Cost</p>
                <p className="text-2xl font-bold">${totalCost.toFixed(4)}</p>
              </div>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Executions</p>
                <p className="text-2xl font-bold">{totalExecutions}</p>
              </div>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">
                  Avg Success Rate
                </p>
                <p className="text-2xl font-bold">
                  {(avgSuccessRate * 100).toFixed(1)}%
                </p>
              </div>
              <BarChart2 className="h-4 w-4 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Agents</p>
                <p className="text-2xl font-bold">{agents.length}</p>
              </div>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Agent Performance Grid */}
      {agents.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent) => (
              <Card key={agent.agent_name}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">
                    {agent.agent_name}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Success Rate</span>
                    <span>{(agent.success_rate * 100).toFixed(1)}%</span>
                  </div>
                  <Progress
                    value={agent.success_rate * 100}
                    className="h-1.5"
                  />
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-muted-foreground">Executions:</span>{" "}
                      {agent.total_executions}
                    </div>
                    <div>
                      <span className="text-muted-foreground">Cost:</span> $
                      {agent.total_cost_usd.toFixed(4)}
                    </div>
                    <div>
                      <span className="text-muted-foreground">Avg Cost:</span> $
                      {agent.avg_cost_usd.toFixed(4)}
                    </div>
                    <div>
                      <span className="text-muted-foreground">
                        Avg Duration:
                      </span>{" "}
                      {agent.avg_duration_seconds.toFixed(1)}s
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Comparison Table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Agent Comparison</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Agent</TableHead>
                    <TableHead className="text-right">Executions</TableHead>
                    <TableHead className="text-right">Success %</TableHead>
                    <TableHead className="text-right">Avg Cost</TableHead>
                    <TableHead className="text-right">Total Cost</TableHead>
                    <TableHead className="text-right">Avg Duration</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {agents.map((agent) => (
                    <TableRow key={agent.agent_name}>
                      <TableCell>
                        <Badge variant="outline">{agent.agent_name}</Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {agent.total_executions}
                      </TableCell>
                      <TableCell className="text-right">
                        {(agent.success_rate * 100).toFixed(1)}%
                      </TableCell>
                      <TableCell className="text-right">
                        ${agent.avg_cost_usd.toFixed(4)}
                      </TableCell>
                      <TableCell className="text-right">
                        ${agent.total_cost_usd.toFixed(4)}
                      </TableCell>
                      <TableCell className="text-right">
                        {agent.avg_duration_seconds.toFixed(1)}s
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      ) : (
        <EmptyState
          icon={BarChart2}
          title="No agent metrics available. Run some workflows to see performance data."
        />
      )}
    </div>
  );
}

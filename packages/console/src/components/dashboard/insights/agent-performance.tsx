import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { DashboardOverview } from "@/types/api";
import { fmtCost, humanize } from "../helpers";

export interface AgentPerformanceProps {
  data: DashboardOverview | undefined;
}

export function AgentPerformance({ data }: AgentPerformanceProps) {
  const agents = data?.agents ?? [];

  if (agents.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">
            Agent Performance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">No agent data yet</p>
        </CardContent>
      </Card>
    );
  }

  const top5 = [...agents]
    .sort((a, b) => b.total_tokens - a.total_tokens)
    .slice(0, 5);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Agent Performance</CardTitle>
        <CardDescription>Top {top5.length} by usage</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-0">
          {/* Header */}
          <div className="grid grid-cols-[1fr_auto_auto_auto] gap-2 text-[10px] text-muted-foreground font-medium pb-1.5 border-b">
            <span>Agent</span>
            <span className="text-right w-8">Runs</span>
            <span className="text-right w-10">Rate</span>
            <span className="text-right w-12">Cost</span>
          </div>
          {/* Rows */}
          {top5.map((agent) => {
            const rate = Math.round(agent.success_rate * 100);
            return (
              <div
                key={agent.agent_name}
                className="grid grid-cols-[1fr_auto_auto_auto] gap-2 text-xs py-1.5 border-b border-border/50 last:border-0"
              >
                <span className="truncate font-medium">
                  {humanize(agent.agent_name)}
                </span>
                <span className="text-right text-muted-foreground tabular-nums w-8">
                  {agent.executions}
                </span>
                <span
                  className={`text-right tabular-nums w-10 font-medium ${
                    rate > 90
                      ? "text-green-600 dark:text-green-400"
                      : rate > 70
                        ? "text-amber-600 dark:text-amber-400"
                        : "text-red-600 dark:text-red-400"
                  }`}
                >
                  {rate}%
                </span>
                <span className="text-right text-muted-foreground tabular-nums w-12">
                  {fmtCost(agent.total_cost_usd)}
                </span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

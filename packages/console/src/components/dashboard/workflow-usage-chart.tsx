/**
 * WorkflowUsageChart — minimal horizontal bar chart for agent executions.
 * No card chrome — just a section with inline bars.
 */

import type { DashboardOverview } from "@/types/dashboard";

interface WorkflowUsageChartProps {
  data: DashboardOverview | undefined;
}

function rateColor(rate: number): string {
  if (rate >= 0.9) return "bg-green-500";
  if (rate >= 0.7) return "bg-yellow-500";
  return "bg-red-500";
}

export function WorkflowUsageChart({ data }: WorkflowUsageChartProps) {
  const agents = data?.agents ?? [];

  if (agents.length === 0) return null;

  const maxExecs = Math.max(...agents.map((a) => a.executions), 1);

  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-wider font-medium text-muted-foreground mb-3">
        Agent Usage
      </h3>

      <div className="space-y-2">
        {agents.slice(0, 8).map((agent) => (
          <div key={agent.agent_name} className="flex items-center gap-3">
            <span className="text-xs text-muted-foreground w-24 truncate shrink-0">
              {agent.agent_name}
            </span>
            <div className="flex-1 h-1.5 rounded-full bg-muted/30 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${rateColor(agent.success_rate)}`}
                style={{
                  width: `${(agent.executions / maxExecs) * 100}%`,
                }}
              />
            </div>
            <span className="text-[10px] tabular-nums text-muted-foreground w-6 text-right shrink-0">
              {agent.executions}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

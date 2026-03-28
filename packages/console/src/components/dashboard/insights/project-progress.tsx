import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Activity } from "lucide-react";
import type { DashboardOverview } from "@/types/api";
import { PROGRESS_SEGMENTS, type FeatureStats } from "../helpers";

export interface ProjectProgressProps {
  data: DashboardOverview | undefined;
}

export function ProjectProgress({ data }: ProjectProgressProps) {
  const stats: FeatureStats = data?.stats?.features || {
    total: 0,
    backlog: 0,
    planned: 0,
    in_progress: 0,
    review: 0,
    blocked: 0,
    done: 0,
    failed: 0,
    total_cost: 0,
    total_tokens: 0,
  };
  const completionPct = data?.completion_pct ?? 0;

  if (stats.total === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">
            Project Progress
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-4 text-sm text-muted-foreground">
            <Activity className="h-6 w-6 text-muted-foreground/30 mb-2" />
            No features yet
          </div>
        </CardContent>
      </Card>
    );
  }

  const activeSegments = PROGRESS_SEGMENTS.filter(
    (s) => (stats[s.key] as number) > 0,
  );

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">
            Project Progress
          </CardTitle>
          <span className="text-2xl font-bold tabular-nums">
            {completionPct}%
          </span>
        </div>
        <CardDescription>
          {stats.done}/{stats.total} features completed
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Stacked horizontal bar */}
        <div className="h-2.5 rounded-full bg-muted overflow-hidden flex">
          {activeSegments.map((seg) => {
            const count = stats[seg.key] as number;
            const pct = (count / stats.total) * 100;
            return (
              <div
                key={seg.key}
                className={`h-full ${seg.barColor} first:rounded-l-full last:rounded-r-full`}
                style={{ width: `${pct}%` }}
                title={`${seg.label}: ${count}`}
              />
            );
          })}
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          {activeSegments.map((seg) => (
            <span
              key={seg.key}
              className="inline-flex items-center gap-1 text-[10px] text-muted-foreground"
            >
              <span className={`h-1.5 w-1.5 rounded-full ${seg.dotColor}`} />
              {seg.label} {stats[seg.key] as number}
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

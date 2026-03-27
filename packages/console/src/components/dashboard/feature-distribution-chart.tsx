/**
 * FeatureDistributionChart — compact stacked progress bar + legend.
 * No card wrapper, just a section with a horizontal bar.
 */

import { PROGRESS_SEGMENTS, type FeatureStats } from "./helpers";
import type { DashboardOverview } from "@/types/api";

const SEGMENT_HEX: Record<string, string> = {
  "bg-slate-300": "#cbd5e1",
  "bg-blue-300": "#93c5fd",
  "bg-blue-500": "#3b82f6",
  "bg-amber-400": "#fbbf24",
  "bg-red-400": "#f87171",
  "bg-green-500": "#22c55e",
  "bg-red-600": "#dc2626",
};

interface FeatureDistributionChartProps {
  data: DashboardOverview | undefined;
}

export function FeatureDistributionChart({
  data,
}: FeatureDistributionChartProps) {
  const features: FeatureStats = data?.stats?.features ?? {
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

  const segments = PROGRESS_SEGMENTS.map((seg) => ({
    ...seg,
    value: features[seg.key],
    hex: SEGMENT_HEX[seg.barColor] ?? "#94a3b8",
  })).filter((s) => s.value > 0);

  if (segments.length === 0) {
    return (
      <section>
        <h3 className="text-[11px] uppercase tracking-wider font-medium text-muted-foreground mb-3">
          Features
        </h3>
        <p className="text-xs text-muted-foreground">No features yet</p>
      </section>
    );
  }

  const total = segments.reduce((sum, s) => sum + s.value, 0);

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[11px] uppercase tracking-wider font-medium text-muted-foreground">
          Features
        </h3>
        <span className="text-xs tabular-nums text-muted-foreground">
          {Math.round(completionPct)}% complete
        </span>
      </div>

      {/* Stacked horizontal bar */}
      <div className="flex h-2 rounded-full overflow-hidden bg-muted/30">
        {segments.map((seg) => (
          <div
            key={seg.key}
            className="h-full transition-all duration-300"
            style={{
              width: `${(seg.value / total) * 100}%`,
              backgroundColor: seg.hex,
            }}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
        {segments.map((seg) => (
          <div key={seg.key} className="flex items-center gap-1 text-[10px]">
            <span
              className="inline-block h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: seg.hex }}
            />
            <span className="text-muted-foreground">
              {seg.label} {seg.value}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

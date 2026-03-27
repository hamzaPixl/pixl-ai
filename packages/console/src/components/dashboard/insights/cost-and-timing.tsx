/**
 * CostAndTiming — flat stat rows, no card wrapper.
 */

import type { DashboardOverview } from "@/types/api";
import { fmtCost, fmtTokens } from "../helpers";

export interface CostAndTimingProps {
  data: DashboardOverview | undefined;
}

export function CostAndTiming({ data }: CostAndTimingProps) {
  const cost = data?.cost;
  const timing = data?.timing;

  if (!cost && !timing) return null;

  const topModels = cost
    ? Object.entries(cost.by_model)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 2)
    : [];

  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-wider font-medium text-muted-foreground mb-3">
        Cost & Timing
      </h3>

      <div className="space-y-2">
        {cost && (
          <>
            <Row label="Total Cost" value={fmtCost(cost.total_cost_usd)} bold />
            <Row
              label="Tokens"
              value={`${fmtTokens(cost.input_tokens)} in / ${fmtTokens(cost.output_tokens)} out`}
            />
            {topModels.map(([model, modelCost]) => (
              <Row key={model} label={model} value={fmtCost(modelCost)} />
            ))}
          </>
        )}

        {cost && timing && <div className="h-px bg-border/50 my-1" />}

        {timing && (
          <>
            <Row
              label="Avg Duration"
              value={
                timing.avg_session_duration_minutes != null
                  ? `${Math.round(timing.avg_session_duration_minutes)}m`
                  : "\u2014"
              }
              bold
            />
            {timing.median_session_duration_minutes != null && (
              <Row
                label="Median"
                value={`${Math.round(timing.median_session_duration_minutes)}m`}
              />
            )}
            {timing.avg_stage_duration_seconds != null && (
              <Row
                label="Avg Stage"
                value={`${Math.round(timing.avg_stage_duration_seconds)}s`}
              />
            )}
          </>
        )}
      </div>
    </section>
  );
}

function Row({
  label,
  value,
  bold,
}: {
  label: string;
  value: string;
  bold?: boolean;
}) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span
        className={`tabular-nums ${bold ? "font-semibold" : "text-muted-foreground"}`}
      >
        {value}
      </span>
    </div>
  );
}

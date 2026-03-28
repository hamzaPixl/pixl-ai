/**
 * MetricCards — horizontal KPI strip. No card borders — just values with labels.
 * Linear-style: flat, tight, monochrome with subtle color accents.
 */

import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { DashboardSummary, CostBreakdown } from "@/types/api";

interface MetricCardsProps {
  stats: DashboardSummary["stats"];
  cost?: CostBreakdown;
  completionPct?: number;
  activeSessionCount?: number;
  isLoading?: boolean;
}

function formatTokens(n: number): string {
  if (n === 0) return "0";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatUsd(n: number): string {
  if (n < 0.01 && n > 0) return "<$0.01";
  return `$${n.toFixed(2)}`;
}

function rateColor(pct: number): string {
  if (pct >= 80) return "text-green-600 dark:text-green-400";
  if (pct >= 50) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
}

interface MetricProps {
  label: string;
  value: string;
  valueClassName?: string;
  isLoading?: boolean;
}

function Metric({ label, value, valueClassName, isLoading }: MetricProps) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      {isLoading ? (
        <Skeleton className="h-5 w-14 mt-0.5" />
      ) : (
        <span
          className={cn(
            "text-lg font-semibold tabular-nums leading-tight",
            valueClassName,
          )}
        >
          {value}
        </span>
      )}
    </div>
  );
}

export function MetricCards({
  stats,
  cost,
  completionPct,
  activeSessionCount,
  isLoading,
}: MetricCardsProps) {
  const totalFeatures = stats.features.total;
  const doneFeatures = stats.features.done;
  const failedFeatures = stats.features.failed;
  const successRate =
    totalFeatures > 0
      ? Math.round((doneFeatures / (doneFeatures + failedFeatures || 1)) * 100)
      : 0;

  const totalTokens = cost?.total_tokens ?? stats.features.total_tokens ?? 0;
  const totalCost = cost?.total_cost_usd ?? stats.features.total_cost ?? 0;
  const pct = completionPct ?? 0;
  const sessions =
    activeSessionCount ?? stats.features.in_progress + stats.features.review;

  return (
    <div className="flex flex-wrap items-end gap-6 py-4 border-b border-border/50">
      <Metric
        label="Completion"
        value={`${Math.round(pct)}%`}
        valueClassName={rateColor(pct)}
        isLoading={isLoading}
      />
      <Metric label="Active" value={String(sessions)} isLoading={isLoading} />
      <Metric
        label="Success"
        value={`${successRate}%`}
        valueClassName={rateColor(successRate)}
        isLoading={isLoading}
      />
      <Metric label="Cost" value={formatUsd(totalCost)} isLoading={isLoading} />
      <Metric
        label="Tokens"
        value={formatTokens(totalTokens)}
        isLoading={isLoading}
      />
      <Metric
        label="Features"
        value={`${doneFeatures}/${totalFeatures}`}
        isLoading={isLoading}
      />
    </div>
  );
}

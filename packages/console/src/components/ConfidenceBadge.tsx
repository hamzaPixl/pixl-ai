/**
 * Small visual badge showing confidence score (0-100%) with color coding.
 * Red < 50%, yellow 50-80%, green > 80%.
 */

import { cn } from "@/lib/utils";

interface ConfidenceBadgeProps {
  score: number; // 0-100
  className?: string;
}

export function ConfidenceBadge({ score, className }: ConfidenceBadgeProps) {
  const clamped = Math.max(0, Math.min(100, score));

  const colorClass =
    clamped >= 80
      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
      : clamped >= 50
        ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
        : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        colorClass,
        className
      )}
      aria-label={`Confidence: ${clamped}%`}
    >
      {clamped}%
    </span>
  );
}

export interface FeatureStats {
  total: number;
  backlog: number;
  planned: number;
  in_progress: number;
  review: number;
  blocked: number;
  done: number;
  failed: number;
  total_cost: number;
  total_tokens: number;
}

type SegmentKey = keyof Pick<
  FeatureStats,
  "backlog" | "planned" | "in_progress" | "review" | "blocked" | "done" | "failed"
>;

export const PROGRESS_SEGMENTS: Array<{
  key: SegmentKey;
  label: string;
  barColor: string;
  dotColor: string;
}> = [
  { key: "backlog", label: "Backlog", barColor: "bg-slate-300", dotColor: "bg-slate-400" },
  { key: "planned", label: "Planned", barColor: "bg-blue-300", dotColor: "bg-blue-400" },
  { key: "in_progress", label: "In Progress", barColor: "bg-blue-500", dotColor: "bg-blue-500" },
  { key: "review", label: "Review", barColor: "bg-amber-400", dotColor: "bg-amber-400" },
  { key: "blocked", label: "Blocked", barColor: "bg-red-400", dotColor: "bg-red-400" },
  { key: "done", label: "Done", barColor: "bg-green-500", dotColor: "bg-green-500" },
  { key: "failed", label: "Failed", barColor: "bg-red-600", dotColor: "bg-red-600" },
];

export function fmtTokens(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return Math.round(value).toString();
}

export function fmtCost(value: number): string {
  if (!Number.isFinite(value)) return "$0.00";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

export function greeting(now: Date = new Date()): string {
  const hour = now.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function humanize(input: string): string {
  return input
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

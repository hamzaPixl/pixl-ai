import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { formatDuration, formatTokens } from "@/lib/format-utils";
import type { HeartbeatRun } from "@/types/api";

const STATUS_CONFIG: Record<
  string,
  { label: string; className: string; pulse?: boolean }
> = {
  active: {
    label: "Active",
    className: "bg-blue-500 text-white",
    pulse: true,
  },
  completed: {
    label: "Completed",
    className: "bg-green-600 text-white",
  },
  failed: {
    label: "Failed",
    className: "bg-red-600 text-white",
  },
  stalled: {
    label: "Stalled",
    className: "bg-amber-500 text-white",
  },
  cancelled: {
    label: "Cancelled",
    className: "bg-muted text-muted-foreground",
  },
};

function computeDuration(run: HeartbeatRun): string {
  const start = new Date(run.started_at).getTime();
  const end = run.ended_at ? new Date(run.ended_at).getTime() : Date.now();
  const seconds = Math.max(0, Math.floor((end - start) / 1000));
  return formatDuration(seconds);
}

function formatCost(cost: number): string {
  if (cost <= 0) return "-";
  if (cost < 0.01) return "< $0.01";
  return `$${cost.toFixed(2)}`;
}

export function RunList({
  runs,
  selectedRunId,
  onSelect,
}: {
  runs: HeartbeatRun[];
  selectedRunId?: string;
  onSelect: (run: HeartbeatRun) => void;
}) {
  if (runs.length === 0) {
    return (
      <div className="px-3 py-6 text-center text-xs text-muted-foreground">
        No runs yet
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      {runs.map((run) => {
        const config = STATUS_CONFIG[run.status] ?? STATUS_CONFIG.cancelled;
        const isSelected = run.id === selectedRunId;

        return (
          <button
            key={run.id}
            type="button"
            onClick={() => onSelect(run)}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors",
              "hover:bg-accent/50",
              isSelected && "bg-accent"
            )}
            aria-current={isSelected ? "true" : undefined}
            data-testid={`run-item-${run.id}`}
          >
            <Badge
              className={cn(
                "shrink-0 text-[10px]",
                config.className,
                config.pulse && "animate-pulse"
              )}
            >
              {config.label}
            </Badge>

            <div className="flex min-w-0 flex-1 items-center gap-3">
              <span className="text-xs text-muted-foreground">
                {computeDuration(run)}
              </span>
              <span className="text-xs text-muted-foreground">
                {formatTokens(run.total_tokens)}
              </span>
              <span className="text-xs text-muted-foreground">
                {formatCost(run.cost_usd)}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}

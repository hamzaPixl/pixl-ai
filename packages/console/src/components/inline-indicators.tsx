import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { type HealthStatus, HEALTH_DOT_COLORS } from '@/lib/format-utils';

/** Compact stat bar shown above tables. */
export function StatBar({ items }: { items: Array<{ label: string; value: string | number }> }) {
  return (
    <div className="flex items-center gap-3 text-xs text-muted-foreground px-1">
      {items.map((item, i) => (
        <span key={i}>
          {i > 0 && <span className="mr-3">·</span>}
          <span className="tabular-nums font-medium text-foreground/70">{item.value}</span>{' '}
          {item.label}
        </span>
      ))}
    </div>
  );
}

/** 8px health dot with tooltip. */
export function HealthDot({ status, tooltip }: { status: HealthStatus; tooltip?: string }) {
  const dot = (
    <span
      className={`inline-block w-2 h-2 rounded-full shrink-0 ${HEALTH_DOT_COLORS[status]}`}
    />
  );
  if (!tooltip) return dot;
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>{dot}</TooltipTrigger>
        <TooltipContent><p className="text-xs">{tooltip}</p></TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/** Mini progress bar (4px tall). */
export function MiniProgressBar({
  segments,
  className,
}: {
  segments: Array<{ fraction: number; color: string; label?: string }>;
  className?: string;
}) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={`h-1 w-full rounded-full bg-muted overflow-hidden flex ${className ?? ''}`}>
            {segments.map((seg, i) =>
              seg.fraction > 0 ? (
                <div
                  key={i}
                  className={`h-full ${seg.color} transition-all`}
                  style={{ width: `${Math.max(seg.fraction * 100, 2)}%` }}
                />
              ) : null,
            )}
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <div className="text-xs space-y-0.5">
            {segments.filter(s => s.fraction > 0).map((seg, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <span className={`inline-block w-2 h-2 rounded-sm ${seg.color}`} />
                <span>{seg.label ?? `${Math.round(seg.fraction * 100)}%`}</span>
              </div>
            ))}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/** Segmented stage progress bar for sessions — each segment is a node. */
export function StageProgressBar({
  nodes,
}: {
  nodes: Record<string, { state: string; node_id: string }>;
}) {
  const entries = Object.values(nodes);
  if (entries.length === 0) return <span className="text-xs text-muted-foreground">-</span>;

  const stateColor: Record<string, string> = {
    task_completed: 'bg-green-500',
    task_running: 'bg-blue-500 animate-pulse',
    task_failed: 'bg-red-500',
    task_blocked: 'bg-yellow-500',
    task_paused: 'bg-yellow-500',
    task_pending: 'bg-muted-foreground/20',
    task_skipped: 'bg-muted-foreground/10',
    gate_approved: 'bg-green-500',
    gate_waiting: 'bg-blue-500 animate-pulse',
    gate_rejected: 'bg-red-500',
    gate_pending: 'bg-muted-foreground/20',
    gate_timeout: 'bg-orange-500',
  };

  const completed = entries.filter(n =>
    n.state === 'task_completed' || n.state === 'gate_approved'
  ).length;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-1">
            <div className="flex gap-px h-1.5 flex-1 min-w-[60px] max-w-[120px]">
              {entries.map((node) => (
                <div
                  key={node.node_id}
                  className={`flex-1 rounded-sm ${stateColor[node.state] ?? 'bg-muted-foreground/20'}`}
                />
              ))}
            </div>
            <span className="text-[10px] text-muted-foreground tabular-nums">
              {completed}/{entries.length}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <div className="text-xs space-y-0.5 max-h-48 overflow-y-auto">
            {entries.map(n => (
              <div key={n.node_id} className="flex items-center gap-1.5">
                <span className={`inline-block w-2 h-2 rounded-sm ${stateColor[n.state] ?? 'bg-gray-300'}`} />
                <span className="font-mono">{n.node_id}</span>
                <span className="text-muted-foreground">{n.state.replace(/^(task_|gate_)/, '')}</span>
              </div>
            ))}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/** Stacked feature status bar for epics. */
export function FeatureStatusBar({
  statusCounts,
  total,
}: {
  statusCounts: Record<string, number>;
  total: number;
}) {
  if (total === 0) return <span className="text-xs text-muted-foreground">-</span>;

  const statusColors: Record<string, string> = {
    done: 'bg-green-500',
    in_progress: 'bg-blue-500',
    review: 'bg-yellow-500',
    planned: 'bg-sky-300 dark:bg-sky-700',
    backlog: 'bg-muted-foreground/20',
    failed: 'bg-red-500',
    blocked: 'bg-orange-500',
  };

  const done = statusCounts.done ?? 0;
  const segments = Object.entries(statusCounts)
    .filter(([, count]) => count > 0)
    .map(([status, count]) => ({
      fraction: count / total,
      color: statusColors[status] ?? 'bg-muted-foreground/20',
      label: `${count} ${status}`,
    }));

  return (
    <div className="flex items-center gap-2 min-w-[100px]">
      <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden flex">
        {segments.map((seg, i) => (
          <div
            key={i}
            className={`h-full ${seg.color}`}
            style={{ width: `${seg.fraction * 100}%` }}
          />
        ))}
      </div>
      <span className="text-[10px] text-muted-foreground tabular-nums whitespace-nowrap">
        {done}/{total}
      </span>
    </div>
  );
}

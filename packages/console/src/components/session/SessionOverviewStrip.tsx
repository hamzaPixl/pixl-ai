import { useMemo } from 'react';
import { Clock, ShieldQuestion, FileText, AlertTriangle } from 'lucide-react';
import { StatusBadge } from '@/components/status-badge';
import type { StageInfo } from '@/lib/session-utils';
import type { TraceEvent } from '@/hooks/use-session-trace';

interface SessionOverviewStripProps {
  session: any;
  stages: StageInfo[];
  currentStage: StageInfo | undefined;
  events: TraceEvent[];
  artifactCount: number;
  pendingGatesCount: number;
}

export function SessionOverviewStrip({
  session,
  stages,
  currentStage,
  events,
  artifactCount,
  pendingGatesCount,
}: SessionOverviewStripProps) {
  const runtime = useMemo(() => {
    const totalSeconds = session?.execution_seconds;
    if (totalSeconds == null || totalSeconds === 0) return null;
    if (totalSeconds < 60) return `${Math.floor(totalSeconds)}s`;
    const minutes = Math.floor(totalSeconds / 60);
    const remainingSeconds = Math.floor(totalSeconds % 60);
    if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
  }, [session?.execution_seconds]);

  const lastEvent = useMemo(() => {
    if (events.length === 0) return null;
    const last = events[events.length - 1];
    return last.event_type.replace(/_/g, ' ');
  }, [events]);

  const breakdown = useMemo(() => {
    const completed = stages.filter((s) => s.state === 'completed').length;
    const running = stages.filter((s) => s.state === 'running').length;
    const failed = stages.filter((s) => s.state === 'failed').length;
    const waiting = stages.filter((s) => s.state === 'waiting').length;
    const total = stages.length;
    const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
    return { completed, running, failed, waiting, total, pct };
  }, [stages]);

  if (!session) return null;

  return (
    <div className="flex flex-col gap-2 py-3 border-b">
      {/* Single row: status + inline stats + progress bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <StatusBadge status={session.status} />

        <Separator />

        {/* Progress fraction */}
        {breakdown.total > 0 && (
          <Stat label="Progress">
            <span className="tabular-nums">{breakdown.completed}/{breakdown.total}</span>
            <span className="text-muted-foreground ml-0.5">({breakdown.pct}%)</span>
          </Stat>
        )}

        {/* Runtime */}
        {runtime && (
          <>
            <Separator />
            <Stat label="Runtime" icon={<Clock className="h-3 w-3" />}>
              <span className="tabular-nums">{runtime}</span>
            </Stat>
          </>
        )}

        {/* Current stage */}
        {currentStage && (
          <>
            <Separator />
            <span className="text-xs text-muted-foreground">
              Stage: <span className="font-medium text-foreground">{currentStage.nodeId}</span>
            </span>
          </>
        )}

        {/* Last event */}
        {lastEvent && (
          <>
            <Separator />
            <span className="text-xs text-muted-foreground truncate max-w-[180px]">
              {lastEvent}
            </span>
          </>
        )}

        {/* Right-aligned counters */}
        <div className="flex items-center gap-3 ml-auto">
          {pendingGatesCount > 0 && (
            <span className="flex items-center gap-1 text-xs font-medium text-yellow-600">
              <ShieldQuestion className="h-3.5 w-3.5" />
              {pendingGatesCount} gate{pendingGatesCount > 1 ? 's' : ''}
            </span>
          )}

          {breakdown.failed > 0 && (
            <span className="flex items-center gap-1 text-xs font-medium text-red-500">
              <AlertTriangle className="h-3.5 w-3.5" />
              {breakdown.failed} failed
            </span>
          )}

          {artifactCount > 0 && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <FileText className="h-3.5 w-3.5" />
              {artifactCount}
            </span>
          )}
        </div>
      </div>

      {/* Full-width stacked progress bar */}
      {breakdown.total > 0 && (
        <div className="h-1.5 rounded-full overflow-hidden flex bg-muted">
          {breakdown.completed > 0 && (
            <div
              className="h-full bg-green-500 transition-all duration-500"
              style={{ width: `${(breakdown.completed / breakdown.total) * 100}%` }}
            />
          )}
          {breakdown.running > 0 && (
            <div
              className="h-full bg-blue-500 transition-all duration-500"
              style={{ width: `${(breakdown.running / breakdown.total) * 100}%` }}
            />
          )}
          {breakdown.failed > 0 && (
            <div
              className="h-full bg-red-500 transition-all duration-500"
              style={{ width: `${(breakdown.failed / breakdown.total) * 100}%` }}
            />
          )}
          {breakdown.waiting > 0 && (
            <div
              className="h-full bg-yellow-500 transition-all duration-500"
              style={{ width: `${(breakdown.waiting / breakdown.total) * 100}%` }}
            />
          )}
        </div>
      )}
    </div>
  );
}

function Stat({
  label,
  icon,
  children,
}: {
  label: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <span className="flex items-center gap-1 text-xs">
      {icon}
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{children}</span>
    </span>
  );
}

function Separator() {
  return <span className="h-3 w-px bg-border" />;
}

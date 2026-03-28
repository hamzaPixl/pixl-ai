/**
 * Human-readable session summary replacing hex session chips.
 * Shows stacked colored dots + count text.
 */

import { Link } from '@tanstack/react-router';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

const SESSION_STATUS_COLORS: Record<string, string> = {
  completed: 'bg-green-500',
  running: 'bg-blue-500',
  failed: 'bg-red-500',
  paused: 'bg-yellow-500',
};

const MAX_DOTS = 5;

interface SessionSummaryProps {
  sessions: Array<{ id: string; status?: string }>;
  projectId: string;
  onClick?: (e: React.MouseEvent) => void;
}

export function SessionSummary({ sessions, projectId, onClick }: SessionSummaryProps) {
  if (sessions.length === 0) return null;

  const activeCount = sessions.filter(
    (s) => s.status === 'running' || s.status === 'created'
  ).length;
  const completedCount = sessions.filter((s) => s.status === 'completed').length;
  const failedCount = sessions.filter((s) => s.status === 'failed').length;

  const dots = sessions.slice(0, MAX_DOTS);
  const label = buildLabel(sessions.length, activeCount, completedCount, failedCount);

  // Single session: link directly
  if (sessions.length === 1) {
    return (
      <Link
        to="/project/$projectId/sessions/$sessionId"
        params={{ projectId, sessionId: sessions[0].id }}
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        onClick={(e) => { e.stopPropagation(); onClick?.(e); }}
      >
        <span
          className={`inline-block w-2 h-2 rounded-full ${
            SESSION_STATUS_COLORS[sessions[0].status ?? ''] ?? 'bg-gray-400'
          }`}
        />
        {label}
      </Link>
    );
  }

  // Multiple sessions: dots + summary
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            onClick={(e) => { e.stopPropagation(); onClick?.(e); }}
          >
            <span className="inline-flex items-center -space-x-0.5">
              {dots.map((s) => (
                <span
                  key={s.id}
                  className={`inline-block w-2 h-2 rounded-full ring-1 ring-background ${
                    SESSION_STATUS_COLORS[s.status ?? ''] ?? 'bg-gray-400'
                  }`}
                />
              ))}
            </span>
            {label}
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom" align="start">
          <div className="space-y-1 text-xs">
            {sessions.map((s) => (
              <Link
                key={s.id}
                to="/project/$projectId/sessions/$sessionId"
                params={{ projectId, sessionId: s.id }}
                className="flex items-center gap-1.5 hover:underline"
              >
                <span
                  className={`inline-block w-1.5 h-1.5 rounded-full ${
                    SESSION_STATUS_COLORS[s.status ?? ''] ?? 'bg-gray-400'
                  }`}
                />
                <span className="font-mono">{s.id.slice(-8)}</span>
                <span className="text-muted-foreground capitalize">{s.status ?? 'unknown'}</span>
              </Link>
            ))}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function buildLabel(
  total: number,
  active: number,
  completed: number,
  failed: number
): string {
  const parts: string[] = [];
  if (active > 0) parts.push(`${active} active`);
  if (completed > 0) parts.push(`${completed} done`);
  if (failed > 0) parts.push(`${failed} failed`);
  const rest = total - active - completed - failed;
  if (rest > 0) parts.push(`${rest} other`);

  return `${total} session${total !== 1 ? 's' : ''}${parts.length > 0 ? ': ' + parts.join(', ') : ''}`;
}

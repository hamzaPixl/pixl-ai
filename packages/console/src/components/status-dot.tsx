/**
 * Status indicator dot with optional pulse animation for active states.
 */

const STATUS_COLORS: Record<string, string> = {
  running: 'bg-blue-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  paused: 'bg-yellow-500',
  stalled: 'bg-orange-500',
  created: 'bg-gray-400',
  cancelled: 'bg-gray-400',
  blocked: 'bg-red-400',
  pending: 'bg-gray-400',
};

const PULSE_STATES = new Set(['running']);

interface StatusDotProps {
  status: string;
  className?: string;
}

export function StatusDot({ status, className }: StatusDotProps) {
  const color = STATUS_COLORS[status] ?? 'bg-gray-400';
  const pulse = PULSE_STATES.has(status);

  if (pulse) {
    return (
      <span className={`relative flex h-2 w-2 ${className ?? ''}`}>
        <span className={`absolute inline-flex h-full w-full animate-ping rounded-full ${color} opacity-75`} />
        <span className={`relative inline-flex h-2 w-2 rounded-full ${color}`} />
      </span>
    );
  }

  return <span className={`inline-block w-2 h-2 rounded-full ${color} ${className ?? ''}`} />;
}

export { STATUS_COLORS };

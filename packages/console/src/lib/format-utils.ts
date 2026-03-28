/** Format relative time from ISO date string. */
export function formatTimeAgo(isoDate: string): string {
  const now = Date.now();
  const then = new Date(isoDate).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  return new Date(isoDate).toLocaleDateString();
}

/** Format duration from total seconds. */
export function formatDuration(totalSeconds: number): string {
  if (totalSeconds <= 0) return '0s';
  if (totalSeconds < 60) return `${Math.floor(totalSeconds)}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);
  if (minutes < 60) return `${minutes}m ${seconds}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

/** Time-in-status color: green <1h, yellow 1-4h, red >4h. */
export function timeInStatusColor(isoDate: string | null): string {
  if (!isoDate) return 'text-muted-foreground';
  const hours = (Date.now() - new Date(isoDate).getTime()) / 3_600_000;
  if (hours < 1) return 'text-green-600 dark:text-green-400';
  if (hours < 4) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

/** Format token count compactly: 1234 → "1.2k", 12345 → "12.3k". */
export function formatTokens(tokens: number): string {
  if (tokens === 0) return '-';
  if (tokens < 1000) return String(tokens);
  if (tokens < 1_000_000) return `${(tokens / 1000).toFixed(1)}k`;
  return `${(tokens / 1_000_000).toFixed(1)}M`;
}

/** Compute health status from feature data + session status. */
export type HealthStatus = 'on_track' | 'stalled' | 'failed' | 'idle';

export function computeFeatureHealth(
  featureStatus: string,
  latestSessionStatus?: string,
  startedAt?: string | null,
): HealthStatus {
  if (featureStatus === 'done') return 'on_track';
  if (featureStatus === 'failed' || featureStatus === 'blocked') return 'failed';
  if (latestSessionStatus === 'failed') return 'failed';
  if (latestSessionStatus === 'stalled') return 'stalled';
  if (featureStatus === 'in_progress' || featureStatus === 'review') {
    if (startedAt) {
      const hours = (Date.now() - new Date(startedAt).getTime()) / 3_600_000;
      if (hours > 4 && latestSessionStatus !== 'running') return 'stalled';
    }
    return 'on_track';
  }
  return 'idle';
}

export const HEALTH_DOT_COLORS: Record<HealthStatus, string> = {
  on_track: 'bg-green-500',
  stalled: 'bg-yellow-500',
  failed: 'bg-red-500',
  idle: 'bg-gray-300 dark:bg-gray-600',
};

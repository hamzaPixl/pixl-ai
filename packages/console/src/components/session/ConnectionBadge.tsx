import { Badge } from '@/components/ui/badge';

export function ConnectionBadge({ state }: { state: string }) {
  const config: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }> = {
    connected: { variant: 'default', label: 'Live' },
    connecting: { variant: 'secondary', label: 'Connecting' },
    reconnecting: { variant: 'outline', label: 'Reconnecting' },
    disconnected: { variant: 'destructive', label: 'Disconnected' },
    error: { variant: 'destructive', label: 'Error' },
  };

  const { variant, label } = config[state] || config.disconnected;

  return (
    <Badge variant={variant}>
      {state === 'connected' && (
        <span className="w-2 h-2 bg-green-500 rounded-full mr-1.5" />
      )}
      {label}
    </Badge>
  );
}

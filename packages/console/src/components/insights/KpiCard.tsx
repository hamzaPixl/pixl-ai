export interface KpiCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  sub?: string;
}

export function KpiCard({ label, value, icon, sub }: KpiCardProps) {
  return (
    <div className="rounded-lg border border-border px-4 py-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-2xl font-semibold tracking-tight">{value}</p>
          <p className="text-xs font-medium text-muted-foreground mt-1">
            {label}
          </p>
          {sub && (
            <p className="text-xs text-muted-foreground/70 mt-1">{sub}</p>
          )}
        </div>
        <div className="text-muted-foreground/50 shrink-0 mt-1">{icon}</div>
      </div>
    </div>
  );
}

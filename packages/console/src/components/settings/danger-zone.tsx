import type { ReactNode } from "react";

interface DangerZoneProps {
  title: string;
  description: string;
  children: ReactNode;
}

export function DangerZone({ title, description, children }: DangerZoneProps) {
  return (
    <div className="rounded-lg border border-destructive/50 p-6 space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-destructive">{title}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>
      {children}
    </div>
  );
}

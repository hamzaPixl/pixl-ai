/**
 * RecoveryAndAutonomy — flat stat rows with subtle color accents.
 */

import type { DashboardOverview } from "@/types/api";
import { cn } from "@/lib/utils";

export interface RecoveryAndAutonomyProps {
  data: DashboardOverview | undefined;
}

export function RecoveryAndAutonomy({ data }: RecoveryAndAutonomyProps) {
  const recovery = data?.recovery;
  const autonomy = data?.autonomy;

  if (!recovery && !autonomy) return null;

  const recoveryRate = recovery
    ? Math.round(recovery.success_rate * 100)
    : null;

  const totalGates = autonomy
    ? autonomy.auto_approved_gates + autonomy.manual_gate_approvals
    : 0;
  const autoRatio =
    totalGates > 0
      ? Math.round((autonomy!.auto_approved_gates / totalGates) * 100)
      : null;

  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-wider font-medium text-muted-foreground mb-3">
        Recovery & Autonomy
      </h3>

      <div className="space-y-2">
        {recovery && recovery.total_incidents > 0 && (
          <>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Recovery Rate</span>
              <span
                className={cn(
                  "font-semibold tabular-nums",
                  recoveryRate! > 80
                    ? "text-green-600 dark:text-green-400"
                    : recoveryRate! > 50
                      ? "text-yellow-600 dark:text-yellow-400"
                      : "text-red-600 dark:text-red-400",
                )}
              >
                {recoveryRate}%
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Incidents</span>
              <span className="text-muted-foreground tabular-nums">
                {recovery.succeeded}/{recovery.total_incidents} resolved
              </span>
            </div>
            {recovery.top_errors.slice(0, 2).map((err) => (
              <div
                key={err.error_type}
                className="flex items-center justify-between text-[10px]"
              >
                <span className="text-muted-foreground truncate mr-2">
                  {err.error_type}
                </span>
                <span className="tabular-nums text-muted-foreground shrink-0">
                  {err.count}x
                </span>
              </div>
            ))}
          </>
        )}

        {recovery && recovery.total_incidents > 0 && autonomy && (
          <div className="h-px bg-border/50 my-1" />
        )}

        {autonomy && (
          <>
            {autoRatio !== null && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Auto-approved</span>
                <span className="font-semibold tabular-nums">{autoRatio}%</span>
              </div>
            )}
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Gates</span>
              <span className="text-muted-foreground tabular-nums">
                {autonomy.auto_approved_gates}/{totalGates}
              </span>
            </div>
            {autonomy.human_interventions > 0 && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">
                  Human interventions
                </span>
                <span className="text-muted-foreground tabular-nums">
                  {autonomy.human_interventions}
                </span>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

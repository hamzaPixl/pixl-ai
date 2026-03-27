import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Circle, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { SIGNAL_TYPE_ICON, SIGNAL_TYPE_COLOR } from "@/lib/epic-constants";

export interface SwarmActivityPanelProps {
  chainId: string;
  projectId: string;
  status: string;
}

export function SwarmActivityPanel({
  chainId,
  projectId,
  status,
}: SwarmActivityPanelProps) {
  const { data: signalsData } = useQuery({
    queryKey: ["swarm", "signals", projectId, chainId],
    queryFn: () => api.control.getChainSignals(chainId, { limit: 20 }),
    enabled: !!chainId,
    refetchInterval: status === "running" ? 3000 : false,
  });

  const { data: qualityData } = useQuery({
    queryKey: ["swarm", "quality", projectId, chainId],
    queryFn: () => api.control.getChainQuality(chainId),
    enabled: !!chainId,
    refetchInterval: status === "running" ? 5000 : false,
  });

  const signals = signalsData?.signals ?? [];
  const judgeSignals = signals.filter((s) => s.signal_type === "judge_finding");
  const activitySignals = signals.filter(
    (s) => s.signal_type !== "judge_finding",
  );
  const quality = qualityData?.scores ?? {};

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      {/* Signal Activity Feed */}
      <div className="rounded-md border border-border/60 bg-background p-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Signal Activity
        </p>
        {activitySignals.length === 0 ? (
          <p className="text-xs text-muted-foreground mt-2">No signals yet.</p>
        ) : (
          <div className="mt-2 space-y-1.5 max-h-48 overflow-y-auto">
            {activitySignals.slice(0, 10).map((sig) => {
              const Icon = SIGNAL_TYPE_ICON[sig.signal_type] || Circle;
              const color =
                SIGNAL_TYPE_COLOR[sig.signal_type] || "text-muted-foreground";
              const payload = sig.payload as Record<string, unknown>;
              const summary = payload?.summary
                ? String(payload.summary).slice(0, 80)
                : sig.signal_type.replace(/_/g, " ");
              return (
                <div key={sig.id} className="flex items-start gap-2 text-xs">
                  <Icon className={`h-3.5 w-3.5 mt-0.5 shrink-0 ${color}`} />
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <Badge
                        variant="outline"
                        className="text-[10px] px-1 py-0"
                      >
                        {sig.from_node}
                      </Badge>
                      <span className="text-muted-foreground/70 text-[10px]">
                        {new Date(sig.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-muted-foreground truncate">{summary}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Judge Verdicts + Quality Scores */}
      <div className="rounded-md border border-border/60 bg-background p-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Judge Verdicts & Quality
        </p>
        {judgeSignals.length === 0 && Object.keys(quality).length === 0 ? (
          <p className="text-xs text-muted-foreground mt-2">
            No judge reviews yet.
          </p>
        ) : (
          <div className="mt-2 space-y-2">
            {judgeSignals.map((sig) => {
              const payload = sig.payload as Record<string, unknown>;
              const verdict = String(payload?.verdict || "pass");
              const wave = payload?.wave;
              const findings = (payload?.findings || []) as Array<
                Record<string, string>
              >;
              return (
                <div
                  key={sig.id}
                  className={`rounded border p-2 ${
                    verdict === "block"
                      ? "border-red-300 bg-red-50/60 dark:bg-red-950/20"
                      : verdict === "warn"
                        ? "border-amber-300 bg-amber-50/60 dark:bg-amber-950/20"
                        : "border-green-300 bg-green-50/60 dark:bg-green-950/20"
                  }`}
                >
                  <div className="flex items-center gap-2 text-xs">
                    {verdict === "pass" && (
                      <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                    )}
                    {verdict === "warn" && (
                      <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                    )}
                    {verdict === "block" && (
                      <XCircle className="h-3.5 w-3.5 text-red-500" />
                    )}
                    <span className="font-medium">
                      Wave {wave != null ? Number(wave) + 1 : "?"}: {verdict}
                    </span>
                  </div>
                  {findings.length > 0 && (
                    <ul className="mt-1 space-y-0.5 text-[11px] text-muted-foreground">
                      {findings.slice(0, 3).map((f, i) => (
                        <li key={i}>
                          [{f.category}] {f.description}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
            {Object.keys(quality).length > 0 && (
              <div className="rounded border border-border/60 p-2 mt-2">
                <p className="text-[10px] font-medium text-muted-foreground mb-1">
                  Quality Metrics
                </p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  {Object.entries(quality).map(([metric, value]) => (
                    <div key={metric} className="flex justify-between">
                      <span className="text-muted-foreground">
                        {metric.replace(/_/g, " ")}
                      </span>
                      <span className="font-mono">
                        {typeof value === "number" && value <= 1 && value >= 0
                          ? `${(value * 100).toFixed(0)}%`
                          : String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

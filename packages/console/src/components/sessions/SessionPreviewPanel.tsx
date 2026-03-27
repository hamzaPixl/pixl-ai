import { useRouter } from "@tanstack/react-router";
import { useHeartbeatRuns } from "@/hooks/queries";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatTokens } from "@/lib/format-utils";
import { PanelRightClose } from "lucide-react";

export interface SessionPreviewPanelProps {
  projectId: string;
  sessionId: string;
  onClose: () => void;
}

export function SessionPreviewPanel({
  projectId,
  sessionId,
  onClose,
}: SessionPreviewPanelProps) {
  const router = useRouter();
  const { data: runs, isLoading: runsLoading } = useHeartbeatRuns(
    sessionId,
    projectId,
  );

  return (
    <div className="h-full flex flex-col">
      <div className="shrink-0 flex items-center justify-between px-4 py-3 border-b">
        <div className="min-w-0 flex-1">
          <span className="text-sm font-semibold truncate block">
            {sessionId.slice(-12)}
          </span>
          <span className="text-[10px] font-mono text-muted-foreground">
            {sessionId}
          </span>
        </div>
        <div className="flex gap-1.5 shrink-0">
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs"
            onClick={() =>
              router.navigate({
                to: "/project/$projectId/sessions/$sessionId",
                params: { projectId, sessionId },
              })
            }
          >
            Open
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 w-7 p-0"
            onClick={onClose}
          >
            <PanelRightClose className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4 space-y-4">
        <div>
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
            Heartbeat Runs
          </h4>
          {runsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : runs && runs.length > 0 ? (
            <div className="space-y-2">
              {runs.slice(0, 10).map((run: any) => (
                <div
                  key={run.id ?? run.started_at}
                  className="rounded-md border px-3 py-2 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <Badge
                      variant={
                        run.status === "active"
                          ? "default"
                          : run.status === "completed"
                            ? "secondary"
                            : "destructive"
                      }
                      className="text-[10px] h-4"
                    >
                      {run.status}
                    </Badge>
                    <span className="text-muted-foreground tabular-nums">
                      {run.cost_usd > 0 ? `$${run.cost_usd.toFixed(4)}` : "-"}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-muted-foreground">
                    <span>{formatTokens(run.total_tokens ?? 0)} tokens</span>
                    {run.model && <span className="truncate">{run.model}</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">No runs recorded</p>
          )}
        </div>
      </div>
    </div>
  );
}

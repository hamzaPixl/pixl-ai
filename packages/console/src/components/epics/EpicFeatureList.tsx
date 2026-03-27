import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { StatusBadge } from "@/components/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Circle } from "lucide-react";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import {
  SESSION_STATUS_COLORS,
  FEATURE_STATUS_ICON,
  FEATURE_STATUS_COLOR,
} from "@/lib/epic-constants";

export interface EpicFeatureListProps {
  epicId: string;
  projectId: string;
}

export function EpicFeatureList({ epicId, projectId }: EpicFeatureListProps) {
  const { data: features, isLoading } = useQuery({
    queryKey: queryKeys.views.epicFeatures(projectId, epicId),
    queryFn: () => api.views.epicFeatures(epicId),
    enabled: !!projectId,
  });

  if (isLoading) {
    return (
      <div className="space-y-1 pl-6">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-7 w-full" />
        ))}
      </div>
    );
  }

  if (!features || features.length === 0) {
    return (
      <p className="pl-6 text-sm text-muted-foreground italic">
        No features yet
      </p>
    );
  }

  return (
    <div className="border-t border-border/50 mt-3 pt-3">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-muted-foreground">
            <th className="text-left font-medium pl-1 pb-1.5">Feature</th>
            <th className="text-left font-medium pb-1.5 w-28">Status</th>
            <th className="text-left font-medium pb-1.5 w-24">Priority</th>
            <th className="text-left font-medium pb-1.5 w-32">Session</th>
          </tr>
        </thead>
        <tbody>
          {features.map((f: any) => {
            const status = f.status || "backlog";
            const Icon = FEATURE_STATUS_ICON[status] || Circle;
            const colorClass =
              FEATURE_STATUS_COLOR[status] || "text-muted-foreground";
            const session = f.active_session;

            return (
              <tr
                key={f.id}
                className="border-t border-border/30 hover:bg-muted/30 transition-colors"
              >
                <td className="py-1.5 pl-1">
                  <div className="flex items-center gap-2 min-w-0">
                    <Icon
                      className={`h-3.5 w-3.5 shrink-0 ${colorClass} ${
                        status === "in_progress" ? "animate-spin" : ""
                      }`}
                    />
                    <span className="truncate">{f.title}</span>
                    <span className="text-[10px] text-muted-foreground/60 font-mono shrink-0">
                      {f.id}
                    </span>
                  </div>
                </td>
                <td className="py-1.5">
                  <StatusBadge status={status} />
                </td>
                <td className="py-1.5">
                  <Badge variant="outline" className="text-[11px]">
                    {f.priority || "P2"}
                  </Badge>
                </td>
                <td className="py-1.5">
                  {session ? (
                    <Link
                      to="/project/$projectId/sessions/$sessionId"
                      params={{ projectId, sessionId: session.id }}
                      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[11px] font-mono bg-muted hover:bg-muted/80 transition-colors"
                    >
                      <span
                        className={`inline-block w-1.5 h-1.5 rounded-full ${
                          SESSION_STATUS_COLORS[session.status ?? ""] ??
                          "bg-gray-400 dark:bg-gray-600"
                        }`}
                      />
                      {session.id.slice(-8)}
                    </Link>
                  ) : (
                    <span className="text-[11px] text-muted-foreground/50">
                      --
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

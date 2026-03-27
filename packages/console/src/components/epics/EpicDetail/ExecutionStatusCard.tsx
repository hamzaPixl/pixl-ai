import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EpicExecutionProgressResponse } from "@/types/api";

export interface ExecutionStatusCardProps {
  projectId: string;
  execution: EpicExecutionProgressResponse;
}

export function ExecutionStatusCard({
  projectId,
  execution,
}: ExecutionStatusCardProps) {
  if (execution.error) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Execution Status</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Status:</span>{" "}
            <Badge variant="outline">{execution.status}</Badge>
          </div>
          <div>
            <span className="text-muted-foreground">Wave:</span>{" "}
            {execution.current_wave}/{execution.total_waves}
          </div>
          <div>
            <span className="text-muted-foreground">Completed:</span>{" "}
            {execution.completed_features}/{execution.total_features}
          </div>
          <div>
            <span className="text-muted-foreground">Failed:</span>{" "}
            {execution.failed_features}
          </div>
        </div>
        {execution.results && execution.results.length > 0 && (
          <div className="mt-4 space-y-1">
            {execution.results.map((r) => (
              <div key={r.node_id} className="flex items-center gap-2 text-xs">
                <Badge
                  variant="outline"
                  className={`text-[10px] ${
                    r.status === "completed"
                      ? "bg-green-50 dark:bg-green-900/20"
                      : r.status === "failed"
                        ? "bg-red-50 dark:bg-red-900/20"
                        : r.status === "running"
                          ? "bg-yellow-50 dark:bg-yellow-900/20"
                          : ""
                  }`}
                >
                  {r.status}
                </Badge>
                {r.feature_id ? (
                  <Link
                    to="/project/$projectId/features/$featureId"
                    params={{ projectId, featureId: r.feature_id }}
                    className="font-mono hover:underline"
                  >
                    {r.feature_ref ?? r.feature_id}
                  </Link>
                ) : (
                  <span className="font-mono">
                    {r.feature_ref ?? r.node_id}
                  </span>
                )}
                {r.session_id && (
                  <Link
                    to="/project/$projectId/sessions/$sessionId"
                    params={{
                      projectId,
                      sessionId: r.session_id,
                    }}
                    className="text-primary underline"
                  >
                    {r.session_id}
                  </Link>
                )}
                {r.error && (
                  <span className="text-red-600 dark:text-red-400 truncate">
                    {r.error}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

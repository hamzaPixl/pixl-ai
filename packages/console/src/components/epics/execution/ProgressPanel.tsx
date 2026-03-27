import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Loader2, CheckCircle2, XCircle, Clock, Pause } from "lucide-react";
import type { EpicExecutionProgressResponse } from "@/types/api";

export interface ProgressPanelProps {
  projectId: string;
  progress: EpicExecutionProgressResponse | undefined;
}

function getStatusIcon(status: string) {
  switch (status) {
    case "running":
      return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
    case "completed":
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case "failed":
      return <XCircle className="h-4 w-4 text-red-500" />;
    case "cancelled":
      return <XCircle className="h-4 w-4 text-yellow-500" />;
    case "paused":
      return <Pause className="h-4 w-4 text-orange-500" />;
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
}

export function ProgressPanel({ projectId, progress }: ProgressPanelProps) {
  return (
    <div className="space-y-4 py-4">
      {/* Status bar */}
      <div className="flex items-center justify-between p-3 border rounded-md bg-muted/30">
        <div className="flex items-center gap-2">
          {getStatusIcon(progress?.status || "pending")}
          <span className="font-medium capitalize">
            {progress?.status || "pending"}
          </span>
        </div>
        <Badge variant="outline">
          {progress?.current_wave || 0} / {progress?.total_waves || 0} waves
        </Badge>
      </div>

      {/* Progress bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-sm">
          <span>Progress</span>
          <span className="text-muted-foreground">
            {progress?.completed_features || 0} /{" "}
            {progress?.total_features || 0} features (
            {progress?.progress_pct || 0}%)
          </span>
        </div>
        <Progress value={progress?.progress_pct || 0} className="h-2" />
      </div>

      {/* Feature results */}
      {progress && progress.results.length > 0 && (
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">
            Features
          </label>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {progress.results.map((result) => (
              <div
                key={result.feature_id ?? result.node_id}
                className="flex items-center gap-3 p-2 border rounded-md bg-muted/20"
              >
                {getStatusIcon(result.status || "pending")}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">
                    {result.feature_id ? (
                      <Link
                        to="/project/$projectId/features/$featureId"
                        params={{ projectId, featureId: result.feature_id }}
                        className="hover:underline"
                      >
                        {result.feature_id}
                      </Link>
                    ) : (
                      result.node_id
                    )}
                  </div>
                  {result.error && (
                    <div className="text-xs text-destructive truncate">
                      {result.error}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {progress?.error && (
        <div className="flex items-center gap-2 text-sm text-destructive p-3 border rounded-md">
          <XCircle className="h-4 w-4" />
          <span>{progress.error}</span>
        </div>
      )}
    </div>
  );
}

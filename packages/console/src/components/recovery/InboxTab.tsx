import { Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { recovery } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { LoadingSkeletons } from "@/components/loading-skeletons";
import { toast } from "sonner";
import { RefreshCw, SkipForward, ShieldAlert } from "lucide-react";
import type { RecoveryInboxItem } from "@/types/api";

export interface InboxTabProps {
  projectId: string;
}

export function InboxTab({ projectId }: InboxTabProps) {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.recovery.inbox(projectId),
    queryFn: () => recovery.inbox(),
    enabled: !!projectId,
  });

  const retryMutation = useMutation({
    mutationFn: ({
      sessionId,
      nodeId,
    }: {
      sessionId: string;
      nodeId: string;
    }) => recovery.retry(sessionId, nodeId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.recovery.inbox(projectId),
      });
      toast.success("Retry queued");
    },
    onError: () => toast.error("Retry failed"),
  });

  const skipMutation = useMutation({
    mutationFn: ({
      sessionId,
      nodeId,
    }: {
      sessionId: string;
      nodeId: string;
    }) => recovery.skip(sessionId, nodeId, { reason: "Skipped from UI" }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.recovery.inbox(projectId),
      });
      toast.success("Node skipped");
    },
    onError: () => toast.error("Skip failed"),
  });

  if (isLoading) {
    return <LoadingSkeletons count={3} />;
  }

  const blockers = data?.blockers ?? [];

  if (blockers.length === 0) {
    return (
      <EmptyState
        icon={ShieldAlert}
        title="No blocked nodes — everything is running smoothly"
      />
    );
  }

  return (
    <div className="space-y-3">
      {blockers.map((item: RecoveryInboxItem) => (
        <Card key={`${item.session_id}-${item.node_id}`}>
          <CardContent className="pt-4">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  {item.feature_id ? (
                    <Link
                      to="/project/$projectId/features/$featureId"
                      params={{ projectId, featureId: item.feature_id }}
                      className="font-medium text-sm hover:underline"
                    >
                      {item.feature_title}
                    </Link>
                  ) : (
                    <span className="font-medium text-sm">
                      {item.feature_title}
                    </span>
                  )}
                  <Badge variant="outline" className="text-xs">
                    {item.failure_kind ?? "blocked"}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Session: {item.session_id} → Node: {item.node_id}
                </p>
                <p className="text-xs text-muted-foreground">
                  {item.blocked_reason}
                </p>
                {item.error_message && (
                  <p className="text-xs text-red-600 dark:text-red-400">
                    {item.error_message}
                  </p>
                )}
              </div>
              <div className="flex gap-2 shrink-0">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    retryMutation.mutate({
                      sessionId: item.session_id,
                      nodeId: item.node_id,
                    })
                  }
                  disabled={retryMutation.isPending}
                >
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Retry
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    skipMutation.mutate({
                      sessionId: item.session_id,
                      nodeId: item.node_id,
                    })
                  }
                  disabled={skipMutation.isPending}
                >
                  <SkipForward className="h-3 w-3 mr-1" />
                  Skip
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

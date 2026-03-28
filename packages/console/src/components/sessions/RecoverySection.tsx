import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { recovery } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { LoadingSkeletons } from "@/components/loading-skeletons";
import { EmptyState } from "@/components/empty-state";
import {
  AlertTriangle,
  ChevronDown,
  RefreshCw,
  ShieldAlert,
  SkipForward,
} from "lucide-react";
import { toast } from "sonner";
import type { RecoveryInboxItem } from "@/types/api";

export interface RecoverySectionProps {
  projectId: string;
}

export function RecoverySection({ projectId }: RecoverySectionProps) {
  const [isOpen, setIsOpen] = useState(false);
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

  const blockers = data?.blockers ?? [];

  if (blockers.length === 0 && !isLoading) return null;

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger asChild>
        <button className="flex items-center gap-2 w-full text-left py-2 hover:bg-muted/50 rounded-md px-2 transition-colors">
          <ChevronDown
            className={`h-4 w-4 text-muted-foreground transition-transform ${isOpen ? "" : "-rotate-90"}`}
          />
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <span className="text-sm font-medium">Recovery</span>
          {blockers.length > 0 && (
            <Badge
              variant="destructive"
              className="h-4 min-w-[16px] px-1 text-[10px]"
            >
              {blockers.length}
            </Badge>
          )}
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="pl-8 space-y-3 mt-2">
          {isLoading ? (
            <LoadingSkeletons count={2} />
          ) : blockers.length === 0 ? (
            <EmptyState icon={ShieldAlert} title="No blocked nodes" />
          ) : (
            blockers.map((item: RecoveryInboxItem) => (
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
                        Session: {item.session_id} &rarr; Node: {item.node_id}
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
            ))
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

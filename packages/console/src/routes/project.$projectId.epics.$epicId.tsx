/**
 * Epic Detail page.
 *
 * Shows header with status and actions, feature tree with dependency edges,
 * execution chain progress, signals feed, and history/notes tabs.
 */

import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEpic, useEpicFeatures, useEpicHistory } from "@/hooks/queries";
import { control } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import type { WorkItem } from "@/types/api";
import {
  EpicHeader,
  ExecutionStatusCard,
  EpicDetailTabs,
} from "@/components/epics/EpicDetail";

export const Route = createFileRoute("/project/$projectId/epics/$epicId")({
  component: EpicDetailPage,
});

const statusColors: Record<string, string> = {
  drafting: "bg-muted text-muted-foreground",
  decomposed: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  in_progress:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300",
  completed:
    "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
};

function EpicDetailPage() {
  const { projectId, epicId } = Route.useParams();
  const queryClient = useQueryClient();
  const { data: epic, isLoading } = useEpic(epicId, projectId);
  const { data: features } = useEpicFeatures(epicId, projectId);
  const { data: history } = useEpicHistory(epicId, projectId);

  const { data: execution } = useQuery({
    queryKey: [projectId, "epic-execution", epicId],
    queryFn: () => control.getEpicExecution(epicId),
    enabled: !!projectId && !!epicId,
  });

  const { data: waves } = useQuery({
    queryKey: [projectId, "epic-waves", epicId],
    queryFn: () => control.getEpicWaves(epicId),
    enabled: !!projectId && !!epicId,
  });

  const runMutation = useMutation({
    mutationFn: () => control.runEpic(epicId),
    onSuccess: () => {
      toast.success("Epic execution started");
      queryClient.invalidateQueries({
        queryKey: queryKeys.epics.detail(projectId, epicId),
      });
    },
    onError: () => toast.error("Failed to start epic execution"),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!epic) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <p className="text-muted-foreground">Epic not found.</p>
        <Button variant="ghost" asChild className="mt-4">
          <Link to="/project/$projectId/epics" params={{ projectId }}>
            Back to Epics
          </Link>
        </Button>
      </div>
    );
  }

  const completedFeatures =
    features?.filter((f: WorkItem) => f.status === "done").length ?? 0;
  const totalFeatures = features?.length ?? 0;
  const progressPct =
    totalFeatures > 0 ? (completedFeatures / totalFeatures) * 100 : 0;

  return (
    <div className="space-y-6">
      <EpicHeader
        projectId={projectId}
        epicId={epicId}
        title={epic.title}
        status={epic.status}
        statusColors={statusColors}
        onRun={() => runMutation.mutate()}
        isRunPending={runMutation.isPending}
      />

      {/* Progress card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-muted-foreground">
              Feature Progress
            </span>
            <span className="text-sm font-medium">
              {completedFeatures}/{totalFeatures} done ({progressPct.toFixed(0)}
              %)
            </span>
          </div>
          <Progress value={progressPct} className="h-2" />
        </CardContent>
      </Card>

      {execution && !execution.error && (
        <ExecutionStatusCard projectId={projectId} execution={execution} />
      )}

      <EpicDetailTabs
        projectId={projectId}
        features={features}
        waves={waves}
        history={history}
        notes={(epic as any).notes}
      />
    </div>
  );
}

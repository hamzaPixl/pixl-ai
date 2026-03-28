/**
 * Roadmaps list route with epic detail view.
 */

import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { EpicFeatureTree } from "@/components/EpicFeatureTree";
import { EpicExecutionDialog } from "@/components/EpicExecutionDialog";
import { ChevronRight, Layers } from "lucide-react";
import type { EpicRollup } from "@/types/api";

export const Route = createFileRoute("/project/$projectId/roadmaps")({
  beforeLoad: ({ params }) => {
    throw redirect({ to: "/project/$projectId/roadmap", params });
  },
  component: RoadmapsPage,
});

function RoadmapsPage() {
  const [selectedEpic, setSelectedEpic] = useState<{
    id: string;
    title: string;
  } | null>(null);
  const [executingEpic, setExecutingEpic] = useState<{
    id: string;
    title: string;
  } | null>(null);
  const { projectId } = Route.useParams();

  const { data: dashboardSummary } = useQuery({
    queryKey: queryKeys.dashboard.summary(projectId!),
    queryFn: () => api.dashboard.summary(),
    enabled: !!projectId,
    refetchInterval: 30000,
  });

  // Use views API to get RoadmapRollup with features_total and progress_pct
  const {
    data: roadmaps,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKeys.views.roadmaps(projectId!),
    queryFn: () => api.views.roadmaps(),
    enabled: !!projectId,
  });

  const { data: epicDetail } = useQuery({
    queryKey: queryKeys.views.epic(projectId!, selectedEpic?.id || ""),
    queryFn: () => api.views.epic(selectedEpic!.id),
    enabled: !!projectId && !!selectedEpic,
  });

  const handleViewEpic = (epicId: string, epicTitle: string) => {
    setSelectedEpic({ id: epicId, title: epicTitle });
  };

  const handleRunEpic = (epicId: string) => {
    // Find epic title from available data
    const epicTitle = epicDetail?.title || `Epic ${epicId}`;
    setExecutingEpic({ id: epicId, title: epicTitle });
  };

  const navigate = useNavigate();
  const handleViewFeature = (featureId: string) => {
    navigate({
      to: "/project/$projectId/features/$featureId",
      params: { projectId: projectId!, featureId },
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <PageHeader
          title="Roadmaps"
          description="Strategic plans spanning multiple epics"
        />
        {dashboardSummary?.chains || dashboardSummary?.contracts ? (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="text-xs">
              Active chains:{" "}
              {dashboardSummary?.chains?.chains?.active_chains ?? 0}
            </Badge>
            <Badge variant="outline" className="text-xs">
              Blocked nodes: {dashboardSummary?.chains?.blocked_nodes ?? 0}
            </Badge>
            <Badge variant="outline" className="text-xs">
              Contract complete:{" "}
              {Math.round(
                (dashboardSummary?.contracts?.overall?.ratio ?? 0) * 100,
              )}
              %
            </Badge>
          </div>
        ) : null}
      </div>

      {/* Roadmaps grid */}
      {error ? (
        <div className="text-center py-12">
          <p className="text-destructive">Error: {error.message}</p>
        </div>
      ) : isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-6 w-3/4 mb-2" />
                <Skeleton className="h-4 w-full mb-4" />
                <Skeleton className="h-5 w-20" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : roadmaps && roadmaps.length > 0 ? (
        <div className="space-y-6">
          {roadmaps.map((roadmap) => (
            <Card key={roadmap.id}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <Layers className="h-5 w-5 text-muted-foreground" />
                      <h3 className="text-lg font-semibold">{roadmap.title}</h3>
                      <StatusBadge status={roadmap.status as any} />
                    </div>
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      Strategic roadmap with {roadmap.epic_count} epics
                    </p>
                  </div>
                </div>

                {/* Progress bar */}
                {roadmap.features_total > 0 && (
                  <div className="mb-4">
                    <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                      <span>Progress</span>
                      <span>{roadmap.progress_pct.toFixed(0)}%</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 transition-all"
                        style={{ width: `${roadmap.progress_pct}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Epics list */}
                <RoadmapEpics
                  roadmapId={roadmap.id}
                  projectId={projectId!}
                  onViewEpic={handleViewEpic}
                />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={Layers}
          title="No roadmaps found. Create your first roadmap to get started."
        />
      )}

      {/* Epic Detail Dialog */}
      <Dialog
        open={!!selectedEpic}
        onOpenChange={(open) => !open && setSelectedEpic(null)}
      >
        <DialogContent className="sm:max-w-[700px] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-primary" />
              {selectedEpic?.title}
            </DialogTitle>
            <DialogDescription>
              {epicDetail && (
                <span>
                  {epicDetail.feature_count} feature
                  {epicDetail.feature_count !== 1 ? "s" : ""} •
                  {epicDetail.active_runs > 0 &&
                    ` ${epicDetail.active_runs} running`}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          {selectedEpic && (
            <EpicFeatureTree
              epicId={selectedEpic.id}
              onViewFeature={handleViewFeature}
              onRunEpic={handleRunEpic}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Epic Execution Dialog */}
      {executingEpic && (
        <EpicExecutionDialog
          epicId={executingEpic.id}
          epicTitle={executingEpic.title}
          open={!!executingEpic}
          onOpenChange={(open) => !open && setExecutingEpic(null)}
          onComplete={() => {
            // Refresh epic detail after execution completes
            if (selectedEpic) {
              // Trigger refetch by invalidating query
            }
          }}
        />
      )}
    </div>
  );
}

interface RoadmapEpicsProps {
  roadmapId: string;
  projectId: string;
  onViewEpic: (epicId: string, epicTitle: string) => void;
}

function RoadmapEpics({ roadmapId, projectId, onViewEpic }: RoadmapEpicsProps) {
  const { data: epics, isLoading } = useQuery({
    queryKey: queryKeys.views.epics(projectId!),
    queryFn: () => api.views.epics(),
    enabled: !!projectId,
    select: (data: EpicRollup[]) =>
      data.filter((epic) => epic.roadmap_id === roadmapId),
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (!epics || epics.length === 0) {
    return (
      <p className="text-sm text-muted-foreground italic">
        No epics in this roadmap
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {epics.map((epic) => (
        <div
          key={epic.id}
          className="flex items-center justify-between p-3 rounded-md border hover:bg-muted/50 cursor-pointer transition-colors"
          onClick={() => onViewEpic(epic.id, epic.title)}
        >
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium truncate">{epic.title}</span>
                <StatusBadge status={epic.status as any} />
              </div>
              <p className="text-xs text-muted-foreground">
                {epic.feature_count} feature
                {epic.feature_count !== 1 ? "s" : ""}
                {epic.active_runs > 0 && (
                  <span className="text-blue-500 ml-2">
                    • {epic.active_runs} running
                  </span>
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0 ml-4">
            {Object.entries(epic.features_by_status || {}).map(
              ([status, count]) =>
                count > 0 ? (
                  <Badge key={status} variant="outline" className="text-xs">
                    {status}: {count}
                  </Badge>
                ) : null,
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

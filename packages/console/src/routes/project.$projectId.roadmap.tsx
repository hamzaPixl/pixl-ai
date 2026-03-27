/**
 * Roadmap — Features organized by status with list / kanban / table views.
 */

import { createFileRoute, useRouter } from "@tanstack/react-router";
import { useState, useMemo, useCallback, lazy, Suspense } from "react";
import { useFeatures, useEpics } from "@/hooks/queries";
import { useSessions } from "@/hooks/queries/use-sessions";
import { useUIStore } from "@/stores/ui";
import { features as featuresApi } from "@/lib/api";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { ViewToggle } from "@/components/features/ViewToggle";
const KanbanBoard = lazy(() =>
  import("@/components/features/KanbanBoard").then((m) => ({
    default: m.KanbanBoard,
  })),
);
const FeatureListView = lazy(() =>
  import("@/components/features/FeatureListView").then((m) => ({
    default: m.FeatureListView,
  })),
);
const FeatureTable = lazy(() =>
  import("@/components/features/FeatureTable").then((m) => ({
    default: m.FeatureTable,
  })),
);
import { FeatureDetailSheet } from "@/components/roadmap/FeatureDetailSheet";
import { RunFeatureDialog } from "@/components/RunFeatureDialog";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Map as MapIcon } from "lucide-react";
import type {
  Feature,
  SessionListEntry,
  RunStartResponse,
  FeatureStatus,
} from "@/types/api";

export const Route = createFileRoute("/project/$projectId/roadmap")({
  component: RoadmapPage,
});

function RoadmapPage() {
  const router = useRouter();
  const { projectId } = Route.useParams();
  const {
    data: features,
    isLoading,
    error,
  } = useFeatures(undefined, projectId);
  const { data: epics } = useEpics(undefined, projectId);
  const { data: allSessions } = useSessions(undefined, projectId);
  const { featuresViewMode, setFeaturesViewMode } = useUIStore();

  const [selectedFeature, setSelectedFeature] = useState<Feature | null>(null);
  const [runFeature, setRunFeature] = useState<{
    id: string;
    title: string;
  } | null>(null);

  const queryClient = useQueryClient();
  const transitionMutation = useMutation({
    mutationFn: ({
      featureId,
      newStatus,
    }: {
      featureId: string;
      newStatus: FeatureStatus;
    }) =>
      featuresApi.transition(featureId, {
        to_status: newStatus,
        trigger: "kanban_drag_drop",
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.features.all(projectId),
      });
      toast.success("Status updated", {
        description: `Feature moved to ${variables.newStatus.replace("_", " ")}`,
      });
    },
    onError: (error) => {
      toast.error("Status update failed", {
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.features.all(projectId),
      });
    },
  });

  const sessionsByFeature = useMemo(() => {
    const map = new Map<string, SessionListEntry[]>();
    if (!allSessions) return map;
    for (const session of allSessions) {
      if (!session.feature_id) continue;
      const list = map.get(session.feature_id);
      if (list) list.push(session);
      else map.set(session.feature_id, [session]);
    }
    return map;
  }, [allSessions]);

  const handleFeatureClick = useCallback((feature: Feature) => {
    setSelectedFeature(feature);
  }, []);

  const handleRunClick = useCallback(
    (e: React.MouseEvent, feature: Feature) => {
      e.stopPropagation();
      setRunFeature({ id: feature.id, title: feature.title });
    },
    [],
  );

  const handleRunSuccess = (result: RunStartResponse) => {
    setRunFeature(null);
    router.navigate({
      to: "/project/$projectId/sessions/$sessionId",
      params: { projectId, sessionId: result.session_id },
    });
  };

  const handleFeatureStatusUpdate = (
    featureId: string,
    newStatus: FeatureStatus,
  ) => {
    transitionMutation.mutate({ featureId, newStatus });
  };

  return (
    <div className="space-y-4">
      <PageHeader
        title="Roadmap"
        description="Features organized by status"
        action={
          <ViewToggle
            viewMode={featuresViewMode}
            onViewModeChange={setFeaturesViewMode}
          />
        }
      />

      {/* Content */}
      {error ? (
        <div className="text-center py-12">
          <p className="text-destructive">Error: {error.message}</p>
        </div>
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <Skeleton className="h-5 w-48 mb-2" />
                <Skeleton className="h-4 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : features && features.length > 0 ? (
        <Suspense
          fallback={
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Card key={i}>
                  <CardContent className="p-4">
                    <Skeleton className="h-5 w-48 mb-2" />
                    <Skeleton className="h-4 w-full" />
                  </CardContent>
                </Card>
              ))}
            </div>
          }
        >
          {featuresViewMode === "list" ? (
            <FeatureListView
              features={features}
              epics={epics}
              projectId={projectId}
              sessionsByFeature={sessionsByFeature}
              onFeatureClick={handleFeatureClick}
              onRunClick={handleRunClick}
            />
          ) : featuresViewMode === "table" ? (
            <FeatureTable
              features={features}
              projectId={projectId}
              sessionsByFeature={sessionsByFeature}
              onFeatureClick={handleFeatureClick}
              onRunClick={handleRunClick}
            />
          ) : (
            <KanbanBoard
              features={features}
              projectId={projectId}
              sessionsByFeature={sessionsByFeature}
              onFeatureStatusUpdate={handleFeatureStatusUpdate}
              onFeatureClick={handleFeatureClick}
              onRunClick={handleRunClick}
            />
          )}
        </Suspense>
      ) : (
        <div className="rounded-lg border py-16 text-center text-muted-foreground">
          <MapIcon className="h-8 w-8 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No features yet</p>
        </div>
      )}

      {/* Feature Detail Sheet */}
      <FeatureDetailSheet
        feature={selectedFeature}
        open={!!selectedFeature}
        onOpenChange={(open) => !open && setSelectedFeature(null)}
        projectId={projectId}
        onRun={(f) => {
          setSelectedFeature(null);
          setRunFeature({ id: f.id, title: f.title });
        }}
        sessionsByFeature={sessionsByFeature}
      />

      {/* Run Feature Dialog */}
      {runFeature && (
        <RunFeatureDialog
          featureId={runFeature.id}
          featureTitle={runFeature.title}
          projectId={projectId}
          open={!!runFeature}
          onOpenChange={(open) => !open && setRunFeature(null)}
          onSuccess={handleRunSuccess}
        />
      )}
    </div>
  );
}

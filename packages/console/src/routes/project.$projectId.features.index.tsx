/**
 * Features list page with search, grouping, table/kanban views.
 */

import { createFileRoute, useRouter, redirect } from "@tanstack/react-router";
import {
  useState,
  useMemo,
  useCallback,
  lazy,
  Suspense,
  Component,
  type ReactNode,
  type ErrorInfo,
} from "react";
import { useFeatures } from "@/hooks/queries";
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
import { TableView } from "@/components/features/TableView";
import {
  priorityOrder,
  ALL_PRIORITIES,
  type GroupBy,
} from "@/lib/feature-utils";
import type {
  Feature,
  SessionListEntry,
  RunStartResponse,
  FeatureStatus,
} from "@/types/api";
import type { ViewMode } from "@/components/features/ViewToggle";
import { Card, CardContent } from "@/components/ui/card";
import {
  Empty,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { SearchInput } from "@/components/search-input";
import { LoadingSkeletons } from "@/components/loading-skeletons";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatBar } from "@/components/inline-indicators";
import { RunFeatureDialog } from "@/components/RunFeatureDialog";
import { Search } from "lucide-react";
import {
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { createFeatureColumns } from "@/components/features/feature-columns";

// ─── Error Boundary ───────────────────────────────────────────────────

interface ErrorBoundaryProps {
  children: ReactNode;
}
interface ErrorBoundaryState {
  error: Error | null;
}

class FeaturesErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[FeaturesErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-6 text-center space-y-3">
          <p className="text-sm font-medium text-destructive">
            Something went wrong rendering features.
          </p>
          <p className="text-xs text-muted-foreground font-mono">
            {this.state.error.message}
          </p>
          <button
            type="button"
            className="inline-flex items-center rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
            onClick={() => this.setState({ error: null })}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export const Route = createFileRoute("/project/$projectId/features/")({
  beforeLoad: ({ params }) => {
    throw redirect({ to: "/project/$projectId/roadmap", params });
  },
  component: FeaturesPage,
});

function FeaturesPage() {
  const router = useRouter();
  const { projectId } = Route.useParams();
  const {
    data: features,
    isLoading,
    error,
  } = useFeatures(undefined, projectId);
  const { data: allSessions } = useSessions(undefined, projectId);
  const {
    featuresViewMode,
    setFeaturesViewMode,
    featuresListGroupBy,
    setFeaturesListGroupBy,
    featuresSearchQuery,
    setFeaturesSearchQuery,
  } = useUIStore();

  const [runFeature, setRunFeature] = useState<{
    id: string;
    title: string;
  } | null>(null);
  const selectedPriorities = ALL_PRIORITIES;
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(
    new Set(),
  );
  const [sorting, setSorting] = useState<SortingState>([]);

  // Mutation for status transitions
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
      queryClient.invalidateQueries({
        queryKey: queryKeys.features.detail(projectId, variables.featureId),
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

  // Group sessions by feature_id
  const sessionsByFeature = useMemo(() => {
    const map = new Map<string, SessionListEntry[]>();
    if (!allSessions) return map;
    for (const session of allSessions) {
      if (!session.feature_id) continue;
      const list = map.get(session.feature_id);
      if (list) {
        list.push(session);
      } else {
        map.set(session.feature_id, [session]);
      }
    }
    return map;
  }, [allSessions]);

  // Sort, filter, and search
  const filteredFeatures = useMemo(() => {
    if (!features) return undefined;

    let result = [...features].sort((a, b) => {
      const priorityDiff =
        (priorityOrder[a.priority] ?? 99) - (priorityOrder[b.priority] ?? 99);
      if (priorityDiff !== 0) return priorityDiff;
      return (a.status ?? "").localeCompare(b.status ?? "");
    });

    // Priority filter
    result = result.filter((f) => selectedPriorities.includes(f.priority));

    // Search
    const q = featuresSearchQuery.toLowerCase().trim();
    if (q) {
      result = result.filter(
        (f) =>
          f.title.toLowerCase().includes(q) ||
          (f.description && f.description.toLowerCase().includes(q)) ||
          f.id.toLowerCase().includes(q) ||
          (f.branch_name && f.branch_name.toLowerCase().includes(q)),
      );
    }

    return result;
  }, [features, selectedPriorities, featuresSearchQuery]);

  const featureStats = useMemo(() => {
    if (!filteredFeatures) return null;
    const total = filteredFeatures.length;
    const inProgress = filteredFeatures.filter(
      (f) => f.status === "in_progress",
    ).length;
    const blocked = filteredFeatures.filter(
      (f) => f.status === "blocked",
    ).length;
    const totalCost = filteredFeatures.reduce(
      (sum, f) => sum + (f.total_cost_usd || 0),
      0,
    );
    return { total, inProgress, blocked, totalCost };
  }, [filteredFeatures]);

  const handleFeatureClick = useCallback(
    (feature: Feature) => {
      router.navigate({
        to: "/project/$projectId/features/$featureId",
        params: { projectId, featureId: feature.id },
      });
    },
    [router, projectId],
  );

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

  const handleViewModeChange = (mode: ViewMode) => {
    setFeaturesViewMode(mode);
  };

  const toggleGroup = (key: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const columns = useMemo(
    () =>
      createFeatureColumns({
        projectId,
        sessionsByFeature,
        onRunClick: handleRunClick,
      }),
    [projectId, sessionsByFeature, handleRunClick],
  );

  const table = useReactTable({
    data: filteredFeatures ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="space-y-4">
      {/* Header */}
      <PageHeader
        title="Features"
        description="Individual work items and implementation units"
        action={
          <ViewToggle
            viewMode={featuresViewMode}
            onViewModeChange={handleViewModeChange}
          />
        }
      />

      {/* Search + Filter Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Search */}
        <SearchInput
          value={featuresSearchQuery}
          onChange={setFeaturesSearchQuery}
          placeholder="Search features..."
        />

        {/* Group by (list/table only) */}
        {featuresViewMode !== "kanban" && (
          <Select
            value={featuresListGroupBy}
            onValueChange={(v) => setFeaturesListGroupBy(v as GroupBy)}
          >
            <SelectTrigger className="w-[140px] h-8 text-xs">
              <SelectValue placeholder="Group by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No grouping</SelectItem>
              <SelectItem value="status">Status</SelectItem>
              <SelectItem value="epic">Epic</SelectItem>
              <SelectItem value="type">Type</SelectItem>
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Stat bar */}
      {featureStats && (
        <StatBar
          items={[
            { label: "features", value: featureStats.total },
            { label: "in progress", value: featureStats.inProgress },
            { label: "blocked", value: featureStats.blocked },
            { label: "spent", value: `$${featureStats.totalCost.toFixed(2)}` },
          ]}
        />
      )}

      {/* Features content */}
      <FeaturesErrorBoundary>
        {error ? (
          <div className="text-center py-12">
            <p className="text-destructive">Error: {error.message}</p>
          </div>
        ) : isLoading ? (
          <LoadingSkeletons count={5} variant="card" />
        ) : filteredFeatures && filteredFeatures.length > 0 ? (
          featuresViewMode === "kanban" ? (
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
              <KanbanBoard
                features={filteredFeatures}
                projectId={projectId}
                sessionsByFeature={sessionsByFeature}
                onFeatureStatusUpdate={handleFeatureStatusUpdate}
                onFeatureClick={handleFeatureClick}
                onRunClick={handleRunClick}
              />
            </Suspense>
          ) : (
            <TableView
              table={table}
              groupBy={featuresListGroupBy}
              features={filteredFeatures}
              projectId={projectId}
              sessionsByFeature={sessionsByFeature}
              collapsedGroups={collapsedGroups}
              onToggleGroup={toggleGroup}
              onFeatureClick={handleFeatureClick}
              onRunClick={handleRunClick}
            />
          )
        ) : (
          <Empty className="border">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <Search className="h-5 w-5" />
              </EmptyMedia>
              <EmptyTitle>
                {featuresSearchQuery ? "No matches" : "No features yet"}
              </EmptyTitle>
              <EmptyDescription>
                {featuresSearchQuery
                  ? "No features match your search. Try a different query."
                  : "Create your first feature to get started."}
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        )}
      </FeaturesErrorBoundary>

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

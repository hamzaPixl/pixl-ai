/**
 * Epics page — lists epics with their features and statuses inline.
 */

import { createFileRoute, redirect } from "@tanstack/react-router";
import { useState, useMemo, Fragment } from "react";
import { useQuery } from "@tanstack/react-query";
import { StatusBadge } from "@/components/status-badge";
import { StatBar, FeatureStatusBar } from "@/components/inline-indicators";
import { formatTimeAgo } from "@/lib/format-utils";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { EpicExecutionDialog } from "@/components/EpicExecutionDialog";
import { PageHeader } from "@/components/page-header";
import { SearchInput } from "@/components/search-input";
import { EpicFeatureList } from "@/components/epics/EpicFeatureList";
import { EpicExecutionPlanPanel } from "@/components/epics/EpicExecutionPlanPanel";
import { STATUS_ORDER } from "@/lib/epic-constants";
import { Layers, ChevronDown, ChevronRight, Play } from "lucide-react";

export const Route = createFileRoute("/project/$projectId/epics")({
  beforeLoad: ({ params }) => {
    throw redirect({ to: "/project/$projectId/roadmap", params });
  },
  component: EpicsPage,
});

function EpicsPage() {
  const { projectId } = Route.useParams();
  const [expandedEpics, setExpandedEpics] = useState<Set<string>>(new Set());
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [executingEpic, setExecutingEpic] = useState<{
    id: string;
    title: string;
  } | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const {
    data: epics,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKeys.views.epics(projectId!),
    queryFn: () => api.views.epics(),
    enabled: !!projectId,
  });

  const sortedEpics = epics
    ? [...epics].sort((a, b) => {
        const sa = STATUS_ORDER[a.status] ?? 99;
        const sb = STATUS_ORDER[b.status] ?? 99;
        return sa - sb;
      })
    : undefined;

  const filteredEpics = statusFilter
    ? sortedEpics?.filter((e) => e.status === statusFilter)
    : sortedEpics;

  const searchedEpics = useMemo(() => {
    if (!filteredEpics || !searchQuery) return filteredEpics;
    const q = searchQuery.toLowerCase();
    return filteredEpics.filter(
      (e) =>
        e.title.toLowerCase().includes(q) || e.id.toLowerCase().includes(q),
    );
  }, [filteredEpics, searchQuery]);

  const epicStats = useMemo(() => {
    if (!epics) return null;
    const total = epics.length;
    const inProgress = epics.filter(
      (e: any) => e.status === "in_progress",
    ).length;
    const totalFeatures = epics.reduce(
      (sum: number, e: any) => sum + (e.feature_count ?? 0),
      0,
    );
    const doneFeatures = epics.reduce(
      (sum: number, e: any) => sum + (e.features_by_status?.done ?? 0),
      0,
    );
    const avgCompletion =
      totalFeatures > 0 ? Math.round((doneFeatures / totalFeatures) * 100) : 0;
    return { total, inProgress, avgCompletion };
  }, [epics]);

  const statusCounts = epics?.reduce(
    (acc, e) => {
      acc[e.status] = (acc[e.status] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  const toggleExpand = (epicId: string) => {
    setExpandedEpics((prev) => {
      const next = new Set(prev);
      if (next.has(epicId)) next.delete(epicId);
      else next.add(epicId);
      return next;
    });
  };

  const expandAll = () => {
    if (!searchedEpics) return;
    setExpandedEpics(new Set(searchedEpics.map((e) => e.id)));
  };

  const collapseAll = () => setExpandedEpics(new Set());

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Epics"
        description="Multi-feature scopes with feature breakdown and session tracking"
        action={
          searchedEpics && searchedEpics.length > 0 ? (
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={expandAll}>
                Expand all
              </Button>
              <Button variant="ghost" size="sm" onClick={collapseAll}>
                Collapse all
              </Button>
            </div>
          ) : undefined
        }
      />

      {/* Stat bar */}
      {epicStats && (
        <StatBar
          items={[
            { label: "epics", value: epicStats.total },
            { label: "in progress", value: epicStats.inProgress },
            { label: "avg completion", value: `${epicStats.avgCompletion}%` },
          ]}
        />
      )}

      {/* Status filters + search */}
      {statusCounts && Object.keys(statusCounts).length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-muted-foreground">Status:</span>
          <Button
            variant={statusFilter === null ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter(null)}
          >
            All ({epics?.length || 0})
          </Button>
          {Object.entries(statusCounts).map(([status, count]) => (
            <Button
              key={status}
              variant={statusFilter === status ? "default" : "outline"}
              size="sm"
              onClick={() =>
                setStatusFilter(statusFilter === status ? null : status)
              }
            >
              {status} ({count})
            </Button>
          ))}
          <SearchInput
            value={searchQuery}
            onChange={setSearchQuery}
            placeholder="Search epics..."
          />
        </div>
      )}

      {/* Epic list */}
      {error ? (
        <div className="text-center py-12">
          <p className="text-destructive">Error: {error.message}</p>
        </div>
      ) : isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-5">
                <Skeleton className="h-6 w-64 mb-3" />
                <Skeleton className="h-4 w-full mb-2" />
                <Skeleton className="h-3 w-40" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : searchedEpics && searchedEpics.length > 0 ? (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead style={{ width: 28 }} />
                <TableHead>Title</TableHead>
                <TableHead style={{ width: 100 }}>Status</TableHead>
                <TableHead style={{ width: 180 }}>Features</TableHead>
                <TableHead style={{ width: 70 }}>Active</TableHead>
                <TableHead style={{ width: 80 }}>Blockers</TableHead>
                <TableHead style={{ width: 100 }}>Progress</TableHead>
                <TableHead style={{ width: 80 }}>Age</TableHead>
                <TableHead style={{ width: 70 }} />
              </TableRow>
            </TableHeader>
            <TableBody>
              {searchedEpics.map((epic) => {
                const expanded = expandedEpics.has(epic.id);
                const totalFeatures = epic.feature_count;
                const doneFeatures = epic.features_by_status?.done || 0;
                const progressPct =
                  totalFeatures > 0
                    ? Math.round((doneFeatures / totalFeatures) * 100)
                    : 0;
                return (
                  <Fragment key={epic.id}>
                    <TableRow
                      className="cursor-pointer hover:bg-muted/50"
                      tabIndex={0}
                      role="button"
                      aria-expanded={expanded}
                      onClick={() => toggleExpand(epic.id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          toggleExpand(epic.id);
                        }
                      }}
                    >
                      <TableCell className="px-2">
                        {expanded ? (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="min-w-0">
                          <span className="font-medium truncate block">
                            {epic.title}
                          </span>
                          <span className="text-[10px] font-mono text-muted-foreground">
                            {epic.id}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={epic.status as any} />
                      </TableCell>
                      <TableCell>
                        <FeatureStatusBar
                          statusCounts={epic.features_by_status || {}}
                          total={totalFeatures}
                        />
                      </TableCell>
                      <TableCell>
                        {epic.active_runs > 0 ? (
                          <Badge
                            variant="default"
                            className="bg-blue-500 text-xs"
                          >
                            {epic.active_runs}
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            -
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        {epic.blockers && epic.blockers.length > 0 ? (
                          <Badge variant="destructive" className="text-xs">
                            {epic.blockers.length}
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            -
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        {totalFeatures > 0 ? (
                          <div className="flex items-center gap-1.5">
                            <div className="h-1.5 flex-1 bg-muted rounded-full overflow-hidden">
                              <div
                                className="h-full bg-green-500 transition-all"
                                style={{ width: `${progressPct}%` }}
                              />
                            </div>
                            <span className="text-xs tabular-nums text-muted-foreground w-8 text-right">
                              {progressPct}%
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            -
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="text-xs text-muted-foreground">
                          {epic.created_at
                            ? formatTimeAgo(epic.created_at)
                            : "-"}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs"
                          onClick={(e) => {
                            e.stopPropagation();
                            setExecutingEpic({
                              id: epic.id,
                              title: epic.title,
                            });
                          }}
                        >
                          <Play className="h-3 w-3 mr-1" /> Run
                        </Button>
                      </TableCell>
                    </TableRow>
                    {expanded && (
                      <TableRow>
                        <TableCell colSpan={9} className="p-0">
                          <div className="px-6 py-4 bg-muted/10 border-t">
                            <EpicFeatureList
                              epicId={epic.id}
                              projectId={projectId!}
                            />
                            <EpicExecutionPlanPanel
                              epicId={epic.id}
                              projectId={projectId!}
                            />
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                );
              })}
            </TableBody>
          </Table>
        </div>
      ) : (
        <Card>
          <CardContent className="p-12 text-center">
            <Layers className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground">
              No epics found. Epics are created when you run a prompt classified
              as multi-feature scope.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Epic Execution Dialog */}
      {executingEpic && (
        <EpicExecutionDialog
          epicId={executingEpic.id}
          epicTitle={executingEpic.title}
          open={!!executingEpic}
          onOpenChange={(open) => !open && setExecutingEpic(null)}
          onComplete={() => {
            // Could invalidate epic queries here for fresh data
          }}
        />
      )}
    </div>
  );
}

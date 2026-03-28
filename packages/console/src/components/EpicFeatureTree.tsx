/**
 * Epic Feature Tree - Shows features within an epic with dependencies.
 */

import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useProjectStore, selectCurrentProjectId } from "@/stores/project";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/status-badge";
import {
  ChevronRight,
  ChevronDown,
  Circle,
  CheckCircle2,
  Clock,
  Loader2,
} from "lucide-react";
import { useState } from "react";

interface EpicFeatureTreeProps {
  epicId: string;
  onViewFeature?: (featureId: string) => void;
  onRunEpic?: (epicId: string) => void;
}

export function EpicFeatureTree({
  epicId,
  onViewFeature,
  onRunEpic,
}: EpicFeatureTreeProps) {
  const projectId = useProjectStore(selectCurrentProjectId);

  const { data: features, isLoading } = useQuery({
    queryKey: queryKeys.epics.features(projectId!, epicId),
    queryFn: () => api.views.epicFeatures(epicId),
    enabled: !!projectId && !!epicId,
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="flex items-center gap-2 p-3 border rounded-md"
          >
            <Circle className="h-4 w-4 text-muted-foreground" />
            <div className="flex-1 space-y-1">
              <div className="h-4 w-32 bg-muted rounded animate-pulse" />
              <div className="h-3 w-24 bg-muted rounded animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!features || features.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No features found for this epic
      </div>
    );
  }

  const levels = buildDependencyLevels(features);

  return (
    <div className="space-y-3">
      {/* Run Epic button */}
      {onRunEpic && (
        <div className="flex items-center justify-between pb-2 border-b">
          <span className="text-sm text-muted-foreground">
            {features.length} feature{features.length > 1 ? "s" : ""}
          </span>
          <button
            onClick={() => onRunEpic(epicId)}
            className="px-3 py-1 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Run Epic
          </button>
        </div>
      )}

      <div className="space-y-1">
        {levels.map((level, levelIndex) => (
          <div key={levelIndex} className="flex items-center gap-2">
            {levelIndex > 0 && (
              <div className="flex flex-col items-center py-1">
                <div className="w-px h-4 bg-muted-foreground/30" />
                <Circle className="w-2 h-2 text-muted-foreground/30" />
              </div>
            )}
            <div className="flex-1 space-y-1">
              {level.map((feature) => (
                <FeatureTreeNode
                  key={feature.id}
                  feature={feature}
                  depth={levelIndex}
                  onViewFeature={onViewFeature}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

interface FeatureTreeNodeProps {
  feature: {
    id: string;
    title: string;
    status: string;
    dependencies: Array<{ id: string }>;
    active_session: {
      id: string;
      status: string;
      current_node: string | null;
    } | null;
  };
  depth: number;
  onViewFeature?: (featureId: string) => void;
}

function FeatureTreeNode({
  feature,
  depth,
  onViewFeature,
}: FeatureTreeNodeProps) {
  const projectId = useProjectStore(selectCurrentProjectId);
  const [expanded] = useState(false);

  const statusIcons = {
    backlog: <Clock className="h-4 w-4 text-muted-foreground" />,
    planned: <Circle className="h-4 w-4 text-blue-500" />,
    in_progress: <Loader2 className="h-4 w-4 text-blue-500" />,
    review: <CheckCircle2 className="h-4 w-4 text-yellow-500" />,
    done: <CheckCircle2 className="h-4 w-4 text-green-500" />,
    blocked: <Circle className="h-4 w-4 text-red-500" />,
    failed: <Circle className="h-4 w-4 text-red-500" />,
  };

  const hasActiveSession = feature.active_session !== null;

  return (
    <div
      className={`flex items-start gap-2 py-1.5 rounded-md hover:bg-muted/50 cursor-pointer ${
        hasActiveSession ? "bg-blue-500/5" : ""
      }`}
      style={{ marginLeft: `${depth * 16}px` }}
      onClick={() => onViewFeature?.(feature.id)}
    >
      {expanded ? (
        <ChevronDown className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
      ) : (
        <ChevronRight className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
      )}

      {statusIcons[feature.status as keyof typeof statusIcons] || (
        <Circle className="h-4 w-4 text-muted-foreground" />
      )}

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 text-sm">
          <Link
            to="/project/$projectId/features/$featureId"
            params={{ projectId: projectId!, featureId: feature.id }}
            className="font-medium truncate hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            {feature.title}
          </Link>
          <StatusBadge status={feature.status as any} />
          {hasActiveSession && (
            <Badge variant="outline" className="text-xs">
              Running
            </Badge>
          )}
        </div>

        {/* Dependencies */}
        {feature.dependencies.length > 0 && !expanded && (
          <div className="text-xs text-muted-foreground">
            Depends on: {feature.dependencies.map((d) => d.id).join(", ")}
          </div>
        )}

        {/* Expanded info */}
        {expanded && (
          <div className="mt-2 text-xs text-muted-foreground">
            <div>ID: {feature.id}</div>
            {feature.dependencies.length > 0 && (
              <div>
                Dependencies: {feature.dependencies.map((d) => d.id).join(", ")}
              </div>
            )}
            {hasActiveSession && (
              <div>
                Session: {feature.active_session!.id}
                {feature.active_session!.current_node && (
                  <span>
                    {" "}
                    • Current: {feature.active_session!.current_node}
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Build dependency levels for tree display.
 * Features with no dependencies go in level 0.
 * Each subsequent level contains features whose dependencies are all in previous levels.
 */
function buildDependencyLevels(
  features: EpicFeatureTreeProps["epicId"] extends string ? any[] : any,
) {
  const levels: (typeof features)[] = [];
  const placed = new Set<string>();

  const featureMap = new Map(features.map((f) => [f.id, f] as const));
  const depsMap = new Map(
    features.map((f) => [
      f.id,
      new Set((f.dependencies as Array<{ id: string }>).map((d) => d.id)),
    ]),
  );

  let lastIteration = 0;
  while (placed.size < features.length && lastIteration < features.length + 1) {
    lastIteration++;

    // Find features whose dependencies are all placed
    const level = Array.from(featureMap.entries())
      .filter(([id, _]) => !placed.has(id))
      .filter(([_, f]) => {
        const deps = depsMap.get(f.id) || new Set();
        return Array.from(deps).every((depId: string) => placed.has(depId));
      })
      .map(([, f]) => f);

    if (level.length === 0 && placed.size < features.length) {
      // Circular dependency or unresolvable - place remaining features
      const remaining = Array.from(featureMap.entries())
        .filter(([id]) => !placed.has(id))
        .map(([, f]) => f);
      levels.push(remaining);
      break;
    }

    if (level.length > 0) {
      levels.push(level);
      level.forEach((f) => placed.add(f.id));
    }
  }

  return levels;
}

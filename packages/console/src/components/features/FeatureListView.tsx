/**
 * Linear-style feature list — compact rows with inline metadata.
 * Groups features by status with collapsible sections.
 */

import { useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getFeatureTypeConfig } from "./feature-type-config";
import { formatTimeAgo } from "@/lib/format-utils";
import {
  ChevronRight,
  ChevronDown,
  Play,
  GitBranch,
  ExternalLink,
  Clock,
  DollarSign,
} from "lucide-react";
import type { Feature, SessionListEntry } from "@/types/api";
import type { FeatureStatus } from "@/types/api";

const STATUS_ORDER: FeatureStatus[] = [
  "in_progress",
  "blocked",
  "review",
  "planned",
  "backlog",
  "done",
  "failed",
];

const STATUS_LABELS: Record<FeatureStatus, string> = {
  in_progress: "In Progress",
  blocked: "Blocked",
  review: "Review",
  planned: "Planned",
  backlog: "Backlog",
  done: "Done",
  failed: "Failed",
};

const PRIORITY_CONFIG: Record<string, { label: string; className: string }> = {
  P0: { label: "P0", className: "text-red-500 border-red-500/30 bg-red-500/5" },
  P1: {
    label: "P1",
    className: "text-orange-500 border-orange-500/30 bg-orange-500/5",
  },
  P2: {
    label: "P2",
    className: "text-yellow-500 border-yellow-500/30 bg-yellow-500/5",
  },
  P3: {
    label: "P3",
    className: "text-muted-foreground border-muted bg-muted/30",
  },
};

interface FeatureListViewProps {
  features: Feature[];
  epics?: Array<{ id: string; title: string }>;
  projectId?: string;
  sessionsByFeature: Map<string, SessionListEntry[]>;
  onFeatureClick: (feature: Feature) => void;
  onRunClick: (e: React.MouseEvent, feature: Feature) => void;
}

export function FeatureListView({
  features,
  epics,
  projectId,
  sessionsByFeature,
  onFeatureClick,
  onRunClick,
}: FeatureListViewProps) {
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(
    new Set(),
  );

  const epicMap = useMemo(() => {
    const map = new Map<string, string>();
    if (epics) {
      for (const e of epics) map.set(e.id, e.title);
    }
    return map;
  }, [epics]);

  const grouped = useMemo(() => {
    const groups = new Map<FeatureStatus, Feature[]>();
    for (const status of STATUS_ORDER) {
      const items = features.filter((f) => f.status === status);
      if (items.length > 0) groups.set(status, items);
    }
    return groups;
  }, [features]);

  const toggleSection = (status: string) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(status)) next.delete(status);
      else next.add(status);
      return next;
    });
  };

  return (
    <TooltipProvider>
      <div className="space-y-1">
        {Array.from(grouped.entries()).map(([status, items]) => {
          const collapsed = collapsedSections.has(status);
          return (
            <div key={status}>
              {/* Section header */}
              <button
                type="button"
                onClick={() => toggleSection(status)}
                className="flex items-center gap-2 w-full px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                {collapsed ? (
                  <ChevronRight className="h-3.5 w-3.5" />
                ) : (
                  <ChevronDown className="h-3.5 w-3.5" />
                )}
                <span className="uppercase tracking-wider">
                  {STATUS_LABELS[status]}
                </span>
                <span className="text-muted-foreground/60 tabular-nums">
                  {items.length}
                </span>
              </button>

              {/* Feature rows */}
              {!collapsed && (
                <div className="space-y-px">
                  {items.map((feature) => (
                    <FeatureRow
                      key={feature.id}
                      feature={feature}
                      projectId={projectId}
                      epicName={
                        feature.epic_id
                          ? epicMap.get(feature.epic_id)
                          : undefined
                      }
                      sessionCount={
                        sessionsByFeature.get(feature.id)?.length ?? 0
                      }
                      onClick={() => onFeatureClick(feature)}
                      onRunClick={(e) => onRunClick(e, feature)}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </TooltipProvider>
  );
}

function FeatureRow({
  feature,
  projectId,
  epicName,
  sessionCount,
  onClick,
  onRunClick,
}: {
  feature: Feature;
  projectId?: string;
  epicName?: string;
  sessionCount: number;
  onClick: () => void;
  onRunClick: (e: React.MouseEvent) => void;
}) {
  const typeConfig = getFeatureTypeConfig(feature.type);
  const TypeIcon = typeConfig.icon;
  const priorityConfig = PRIORITY_CONFIG[feature.priority];
  const isRunnable = ["backlog", "planned", "blocked"].includes(feature.status);

  return (
    <div
      onClick={onClick}
      className="group flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted/50 cursor-pointer transition-colors border border-transparent hover:border-border"
    >
      {/* Type icon */}
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={`shrink-0 p-1 rounded ${typeConfig.bg}`}>
            <TypeIcon className={`h-3.5 w-3.5 ${typeConfig.color}`} />
          </div>
        </TooltipTrigger>
        <TooltipContent side="left">
          <p>{typeConfig.label}</p>
        </TooltipContent>
      </Tooltip>

      {/* Priority */}
      {priorityConfig && (
        <Badge
          variant="outline"
          className={`shrink-0 text-[10px] px-1.5 py-0 h-5 font-semibold ${priorityConfig.className}`}
        >
          {priorityConfig.label}
        </Badge>
      )}

      {/* Title + ID */}
      <div className="flex-1 min-w-0 flex items-center gap-2">
        {projectId ? (
          <Link
            to="/project/$projectId/features/$featureId"
            params={{ projectId, featureId: feature.id }}
            className="font-medium text-sm truncate hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            {feature.title}
          </Link>
        ) : (
          <span className="font-medium text-sm truncate">{feature.title}</span>
        )}
        <span className="text-[10px] text-muted-foreground/50 shrink-0 font-mono">
          {feature.id}
        </span>
      </div>

      {/* Metadata pills (right side) */}
      <div className="flex items-center gap-2 shrink-0 opacity-70 group-hover:opacity-100 transition-opacity">
        {/* Epic */}
        {epicName && (
          <Badge
            variant="outline"
            className="text-[10px] px-1.5 py-0 h-5 max-w-[120px] truncate"
          >
            {epicName}
          </Badge>
        )}

        {/* Branch */}
        {feature.branch_name && (
          <Tooltip>
            <TooltipTrigger asChild>
              <GitBranch className="h-3.5 w-3.5 text-muted-foreground" />
            </TooltipTrigger>
            <TooltipContent>
              <p className="font-mono text-xs">{feature.branch_name}</p>
            </TooltipContent>
          </Tooltip>
        )}

        {/* PR link */}
        {feature.pr_url && (
          <Tooltip>
            <TooltipTrigger asChild>
              <a
                href={feature.pr_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="text-muted-foreground hover:text-foreground"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </TooltipTrigger>
            <TooltipContent>
              <p>Open PR</p>
            </TooltipContent>
          </Tooltip>
        )}

        {/* Sessions count */}
        {sessionCount > 0 && (
          <Badge
            variant="outline"
            className="text-[10px] px-1.5 py-0 h-5 tabular-nums"
          >
            {sessionCount} run{sessionCount !== 1 ? "s" : ""}
          </Badge>
        )}

        {/* Cost */}
        {feature.total_cost_usd > 0 && (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="text-[10px] text-muted-foreground tabular-nums flex items-center gap-0.5">
                <DollarSign className="h-3 w-3" />
                {feature.total_cost_usd.toFixed(2)}
              </span>
            </TooltipTrigger>
            <TooltipContent>
              <p>Total cost</p>
            </TooltipContent>
          </Tooltip>
        )}

        {/* Time ago */}
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="text-[10px] text-muted-foreground tabular-nums flex items-center gap-0.5">
              <Clock className="h-3 w-3" />
              {formatTimeAgo(feature.updated_at || feature.created_at)}
            </span>
          </TooltipTrigger>
          <TooltipContent>
            <p>Last updated</p>
          </TooltipContent>
        </Tooltip>

        {/* Run button */}
        {isRunnable && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRunClick}
            className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <Play className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
    </div>
  );
}

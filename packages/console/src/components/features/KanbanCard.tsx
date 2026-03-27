/**
 * Kanban card — Linear-inspired compact card with rich metadata.
 */

import { Link } from "@tanstack/react-router";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Play,
  Layers,
  GitBranch,
  ExternalLink,
  GripVertical,
  AlertCircle,
} from "lucide-react";
import { SessionSummary } from "./SessionSummary";
import { getFeatureTypeConfig } from "./feature-type-config";
import { formatTimeAgo } from "@/lib/format-utils";
import type { KanbanCardProps } from "@/types/dnd";

const PRIORITY_COLORS: Record<string, string> = {
  P0: "text-red-500 bg-red-500/10 border-red-500/20",
  P1: "text-orange-500 bg-orange-500/10 border-orange-500/20",
  P2: "text-yellow-600 bg-yellow-500/10 border-yellow-500/20",
  P3: "text-muted-foreground bg-muted border-muted",
};

export function KanbanCard({
  feature,
  sessionsByFeature,
  projectId,
  isDragOverlay,
  onFeatureClick,
  onRunClick,
}: KanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: feature.id,
    data: { feature },
    disabled: isDragOverlay,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  };

  const typeConfig = getFeatureTypeConfig(feature.type);
  const TypeIcon = typeConfig.icon;
  const featureSessions = sessionsByFeature.get(feature.id) || [];
  const priorityClass = PRIORITY_COLORS[feature.priority] ?? PRIORITY_COLORS.P3;
  const isBlocked = feature.status === "blocked";

  if (isDragOverlay) {
    return (
      <div className="bg-background border rounded-lg shadow-xl ring-1 ring-primary/20 px-3 py-2.5 w-64 sm:w-72">
        <div className="flex items-center gap-2">
          <div className={`p-1 rounded ${typeConfig.bg}`}>
            <TypeIcon className={`h-3.5 w-3.5 ${typeConfig.color}`} />
          </div>
          <span className="text-sm font-medium truncate flex-1">
            {feature.title}
          </span>
          <Badge
            variant="outline"
            className={`shrink-0 text-[10px] h-5 px-1.5 ${priorityClass}`}
          >
            {feature.priority}
          </Badge>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`group relative rounded-md border bg-background hover:bg-accent/50 transition-all cursor-pointer mx-1.5 mb-1.5 ${
        isBlocked ? "border-red-500/30 bg-red-500/5" : "border-border"
      } ${isDragging ? "opacity-30" : ""}`}
      onClick={() => onFeatureClick?.(feature)}
    >
      <div className="px-3 py-2.5">
        {/* Row 1: drag handle + type icon + title + priority */}
        <div className="flex items-start gap-1.5">
          <div
            {...attributes}
            {...listeners}
            className="shrink-0 mt-0.5 opacity-0 group-hover:opacity-60 transition-opacity cursor-grab active:cursor-grabbing"
            onClick={(e) => e.stopPropagation()}
          >
            <GripVertical className="h-3.5 w-3.5 text-muted-foreground" />
          </div>

          <div className={`shrink-0 mt-0.5 p-1 rounded ${typeConfig.bg}`}>
            <TypeIcon className={`h-3 w-3 ${typeConfig.color}`} />
          </div>

          <div className="flex-1 min-w-0">
            <h4 className="text-[13px] font-medium leading-snug line-clamp-2">
              <Link
                to="/project/$projectId/features/$featureId"
                params={{ projectId, featureId: feature.id }}
                className="hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                {feature.title}
              </Link>
            </h4>
          </div>

          <Badge
            variant="outline"
            className={`shrink-0 text-[10px] h-5 px-1.5 font-semibold border ${priorityClass}`}
          >
            {feature.priority}
          </Badge>
        </div>

        {/* Row 2: metadata */}
        <div className="flex items-center gap-1.5 mt-2 ml-6 flex-wrap">
          {/* ID */}
          <span className="text-[10px] font-mono text-muted-foreground/50">
            {feature.id}
          </span>

          {/* Epic */}
          {feature.epic_id && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="inline-flex items-center gap-0.5 text-[10px] text-muted-foreground">
                    <Layers className="h-2.5 w-2.5" />
                    Epic
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="font-mono text-xs">{feature.epic_id}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}

          {/* Branch */}
          {feature.branch_name && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <GitBranch className="h-3 w-3 text-muted-foreground/60" />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="font-mono text-xs">{feature.branch_name}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}

          {/* PR */}
          {feature.pr_url && (
            <a
              href={feature.pr_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-muted-foreground/60 hover:text-foreground transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
            </a>
          )}

          {/* Blocked indicator */}
          {isBlocked && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="inline-flex items-center gap-0.5 text-[10px] text-red-500 font-medium">
                    <AlertCircle className="h-3 w-3" />
                    Blocked
                  </span>
                </TooltipTrigger>
                {feature.blocked_reason && (
                  <TooltipContent>
                    <p className="max-w-xs text-xs">{feature.blocked_reason}</p>
                  </TooltipContent>
                )}
              </Tooltip>
            </TooltipProvider>
          )}

          {/* Cost */}
          {feature.total_cost_usd > 0 && (
            <span className="text-[10px] text-muted-foreground/60 tabular-nums">
              ${feature.total_cost_usd.toFixed(2)}
            </span>
          )}

          {/* Time ago */}
          <span className="text-[10px] text-muted-foreground/40 tabular-nums ml-auto">
            {formatTimeAgo(feature.updated_at || feature.created_at)}
          </span>
        </div>

        {/* Row 3: sessions + run (only if sessions exist or on hover) */}
        {
          <div className="flex items-center gap-1.5 mt-1.5 ml-6">
            {featureSessions.length > 0 && (
              <SessionSummary
                sessions={featureSessions}
                projectId={projectId}
              />
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onRunClick?.(e, feature);
              }}
              className="h-5 px-1.5 text-[10px] opacity-0 group-hover:opacity-100 transition-opacity ml-auto -mr-1"
            >
              <Play className="h-2.5 w-2.5 mr-0.5" />
              Run
            </Button>
          </div>
        }
      </div>
    </div>
  );
}

/**
 * Column definitions for the features table.
 */

import { Link } from "@tanstack/react-router";
import { createColumnHelper, type ColumnDef } from "@tanstack/react-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusBadge, Status } from "@/components/status-badge";
import { HealthDot, MiniProgressBar } from "@/components/inline-indicators";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  formatTimeAgo,
  computeFeatureHealth,
  timeInStatusColor,
  formatTokens,
} from "@/lib/format-utils";
import { Play, ArrowUpDown, ExternalLink } from "lucide-react";
import { getFeatureTypeConfig } from "@/components/features/feature-type-config";
import { priorityOrder } from "@/lib/feature-utils";
import type { Feature, SessionListEntry } from "@/types/api";

const columnHelper = createColumnHelper<Feature>();

export interface FeatureColumnsOptions {
  projectId: string;
  sessionsByFeature: Map<string, SessionListEntry[]>;
  onRunClick: (e: React.MouseEvent, feature: Feature) => void;
}

export function createFeatureColumns({
  projectId,
  sessionsByFeature,
  onRunClick,
}: FeatureColumnsOptions): ColumnDef<Feature, any>[] {
  return [
    columnHelper.display({
      id: "type_icon",
      header: "",
      size: 36,
      cell: ({ row }) => {
        const config = getFeatureTypeConfig(row.original.type);
        const Icon = config.icon;
        return (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <span className={config.color}>
                  <Icon className="h-4 w-4" />
                </span>
              </TooltipTrigger>
              <TooltipContent>
                <p>{config.label}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        );
      },
    }),
    columnHelper.accessor("title", {
      header: "Title",
      cell: ({ row }) => {
        const f = row.original;
        return (
          <div className="min-w-0">
            <span className="font-medium truncate block">{f.title}</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-[10px] font-mono text-muted-foreground">
                {f.id}
              </span>
              {f.branch_name && (
                <Badge
                  variant="outline"
                  className="text-[10px] font-mono h-4 px-1 max-w-[120px] truncate"
                >
                  {f.branch_name}
                </Badge>
              )}
            </div>
            {f.description && (
              <span className="text-[11px] text-muted-foreground line-clamp-1 mt-0.5">
                {f.description}
              </span>
            )}
          </div>
        );
      },
    }),
    columnHelper.accessor("status", {
      header: ({ column }) => (
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 -ml-2"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Status <ArrowUpDown className="ml-1 h-3 w-3" />
        </Button>
      ),
      cell: ({ row }) => {
        const f = row.original;
        const statusDate = f.started_at || f.planned_at || f.created_at;
        return (
          <div className="space-y-0.5">
            <StatusBadge status={f.status as Status} />
            {f.status !== "backlog" && f.status !== "done" && (
              <span
                className={`text-[10px] block ${timeInStatusColor(statusDate)}`}
              >
                {formatTimeAgo(statusDate)}
              </span>
            )}
          </div>
        );
      },
    }),
    columnHelper.accessor("priority", {
      header: ({ column }) => (
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 -ml-2"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Priority <ArrowUpDown className="ml-1 h-3 w-3" />
        </Button>
      ),
      cell: ({ getValue }) => (
        <Badge variant="outline" className="text-xs">
          {getValue()}
        </Badge>
      ),
      sortingFn: (a, b) =>
        priorityOrder[a.original.priority] - priorityOrder[b.original.priority],
    }),
    columnHelper.display({
      id: "progress",
      header: "Progress",
      size: 140,
      cell: ({ row }) => {
        const sessions = sessionsByFeature.get(row.original.id) ?? [];
        if (sessions.length === 0)
          return <span className="text-xs text-muted-foreground">-</span>;
        const latest = sessions[0];
        const nodes = (latest as any).node_instances;
        if (!nodes || Object.keys(nodes).length === 0) {
          return (
            <span className="text-xs text-muted-foreground">
              {sessions.length} session{sessions.length > 1 ? "s" : ""}
            </span>
          );
        }
        const entries = Object.values(nodes) as Array<{ state: string }>;
        const completed = entries.filter(
          (n) => n.state === "task_completed" || n.state === "gate_approved",
        ).length;
        const failed = entries.filter(
          (n) => n.state === "task_failed" || n.state === "gate_rejected",
        ).length;
        const running = entries.filter(
          (n) => n.state === "task_running" || n.state === "gate_waiting",
        ).length;
        const total = entries.length;
        return (
          <MiniProgressBar
            className="max-w-[100px]"
            segments={[
              {
                fraction: completed / total,
                color: "bg-green-500",
                label: `${completed} completed`,
              },
              {
                fraction: running / total,
                color: "bg-blue-500",
                label: `${running} running`,
              },
              {
                fraction: failed / total,
                color: "bg-red-500",
                label: `${failed} failed`,
              },
              {
                fraction: (total - completed - running - failed) / total,
                color: "bg-muted-foreground/20",
                label: `${total - completed - running - failed} pending`,
              },
            ]}
          />
        );
      },
    }),
    columnHelper.display({
      id: "sessions",
      header: "Sessions",
      size: 90,
      cell: ({ row }) => {
        const sessions = sessionsByFeature.get(row.original.id) ?? [];
        if (sessions.length === 0)
          return <span className="text-xs text-muted-foreground">-</span>;
        const latest = sessions[0];
        return (
          <Link
            to="/project/$projectId/sessions/$sessionId"
            params={{ projectId, sessionId: latest.id }}
            onClick={(e) => e.stopPropagation()}
            className="group"
          >
            <span className="text-xs text-primary group-hover:underline tabular-nums">
              {sessions.length} session{sessions.length > 1 ? "s" : ""}
            </span>
            <span className="text-[10px] text-muted-foreground block font-mono">
              {latest.status ?? "unknown"}
            </span>
          </Link>
        );
      },
    }),
    columnHelper.display({
      id: "health",
      header: "",
      size: 32,
      cell: ({ row }) => {
        const f = row.original;
        const sessions = sessionsByFeature.get(f.id) ?? [];
        const latestStatus = sessions[0]?.status;
        const health = computeFeatureHealth(
          f.status,
          latestStatus,
          f.started_at,
        );
        return <HealthDot status={health} tooltip={health.replace("_", " ")} />;
      },
    }),
    columnHelper.accessor("total_cost_usd", {
      header: ({ column }) => (
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 -ml-2"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Cost <ArrowUpDown className="ml-1 h-3 w-3" />
        </Button>
      ),
      cell: ({ row }) => {
        const f = row.original;
        return (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="text-sm text-muted-foreground font-mono">
                  {f.total_cost_usd > 0
                    ? `$${f.total_cost_usd.toFixed(2)}`
                    : "-"}
                </span>
              </TooltipTrigger>
              {f.total_tokens > 0 && (
                <TooltipContent>
                  <p className="text-xs">
                    {formatTokens(f.total_tokens)} tokens
                  </p>
                </TooltipContent>
              )}
            </Tooltip>
          </TooltipProvider>
        );
      },
    }),
    columnHelper.display({
      id: "pr",
      header: "",
      size: 32,
      cell: ({ row }) => {
        if (!row.original.pr_url) return null;
        return (
          <a
            href={row.original.pr_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-muted-foreground hover:text-foreground"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        );
      },
    }),
    columnHelper.display({
      id: "actions",
      header: "",
      size: 70,
      cell: ({ row }) => (
        <Button
          size="sm"
          onClick={(e) => onRunClick(e, row.original)}
          className="h-7 px-3 text-xs gap-1.5 bg-primary/90 hover:bg-primary shadow-sm"
        >
          <Play className="h-3 w-3" /> Run
        </Button>
      ),
    }),
  ];
}

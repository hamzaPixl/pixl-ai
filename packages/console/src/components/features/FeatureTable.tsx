/**
 * Feature data table — clean, dense table with sortable columns.
 * Inspired by Linear's table view with inline indicators.
 */

import { Link } from "@tanstack/react-router";
import type { Feature, SessionListEntry } from "@/types/api";
import { StatusBadge, type Status } from "@/components/status-badge";
import { getFeatureTypeConfig } from "@/components/features/feature-type-config";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { HealthDot, MiniProgressBar } from "@/components/inline-indicators";
import {
  formatTimeAgo,
  formatTokens,
  computeFeatureHealth,
  timeInStatusColor,
} from "@/lib/format-utils";
import { Play, ExternalLink, GitBranch } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const PRIORITY_COLORS: Record<string, string> = {
  P0: "text-red-500 border-red-500/30 bg-red-500/5",
  P1: "text-orange-500 border-orange-500/30 bg-orange-500/5",
  P2: "text-yellow-600 border-yellow-500/30 bg-yellow-500/5",
  P3: "text-muted-foreground border-muted bg-muted/30",
};

export interface FeatureTableProps {
  features: Feature[];
  projectId: string;
  onFeatureClick: (feature: Feature) => void;
  onRunClick: (e: React.MouseEvent, feature: Feature) => void;
  sessionsByFeature: Map<string, SessionListEntry[]>;
}

export function FeatureTable({
  features,
  projectId,
  onFeatureClick,
  onRunClick,
  sessionsByFeature,
}: FeatureTableProps) {
  return (
    <TooltipProvider>
      <div className="rounded-lg border bg-background overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent border-b">
              <TableHead className="w-8" />
              <TableHead className="font-medium text-xs">Feature</TableHead>
              <TableHead className="w-[100px] font-medium text-xs">
                Status
              </TableHead>
              <TableHead className="w-[60px] font-medium text-xs">
                Priority
              </TableHead>
              <TableHead className="w-[130px] font-medium text-xs hidden sm:table-cell">
                Progress
              </TableHead>
              <TableHead className="w-[90px] font-medium text-xs">
                Sessions
              </TableHead>
              <TableHead className="w-8 hidden sm:table-cell" />
              <TableHead className="w-[70px] font-medium text-xs hidden sm:table-cell">
                Cost
              </TableHead>
              <TableHead className="w-[80px] font-medium text-xs hidden sm:table-cell">
                Updated
              </TableHead>
              <TableHead className="w-[60px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {features.map((f) => (
              <FeatureTableRow
                key={f.id}
                feature={f}
                projectId={projectId}
                sessions={sessionsByFeature.get(f.id) ?? []}
                onFeatureClick={onFeatureClick}
                onRunClick={onRunClick}
              />
            ))}
          </TableBody>
        </Table>
      </div>
    </TooltipProvider>
  );
}

function FeatureTableRow({
  feature: f,
  projectId,
  sessions,
  onFeatureClick,
  onRunClick,
}: {
  feature: Feature;
  projectId: string;
  sessions: SessionListEntry[];
  onFeatureClick: (feature: Feature) => void;
  onRunClick: (e: React.MouseEvent, feature: Feature) => void;
}) {
  const config = getFeatureTypeConfig(f.type);
  const Icon = config.icon;
  const statusDate = f.started_at || f.planned_at || f.created_at;
  const latestStatus = sessions[0]?.status;
  const health = computeFeatureHealth(f.status, latestStatus, f.started_at);
  const priorityClass = PRIORITY_COLORS[f.priority] ?? PRIORITY_COLORS.P3;

  const progressCell = buildProgressCell(sessions);

  return (
    <TableRow
      className="group cursor-pointer h-12"
      tabIndex={0}
      onClick={() => onFeatureClick(f)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onFeatureClick(f);
        }
      }}
    >
      {/* Type icon */}
      <TableCell className="pr-0">
        <Tooltip>
          <TooltipTrigger asChild>
            <div className={`p-1 rounded ${config.bg} w-fit`}>
              <Icon className={`h-3.5 w-3.5 ${config.color}`} />
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>{config.label}</p>
          </TooltipContent>
        </Tooltip>
      </TableCell>

      {/* Title + metadata */}
      <TableCell>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Link
              to="/project/$projectId/features/$featureId"
              params={{ projectId, featureId: f.id }}
              className="font-medium text-sm truncate hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {f.title}
            </Link>
            {f.pr_url && (
              <a
                href={f.pr_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="text-muted-foreground/50 hover:text-foreground transition-colors"
              >
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="text-[10px] font-mono text-muted-foreground/50">
              {f.id}
            </span>
            {f.branch_name && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="inline-flex items-center gap-0.5 text-[10px] text-muted-foreground/50">
                    <GitBranch className="h-2.5 w-2.5" />
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="font-mono text-xs">{f.branch_name}</p>
                </TooltipContent>
              </Tooltip>
            )}
          </div>
        </div>
      </TableCell>

      {/* Status */}
      <TableCell>
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
      </TableCell>

      {/* Priority */}
      <TableCell>
        <Badge
          variant="outline"
          className={`text-[10px] h-5 px-1.5 font-semibold ${priorityClass}`}
        >
          {f.priority}
        </Badge>
      </TableCell>

      {/* Progress */}
      <TableCell className="hidden sm:table-cell">{progressCell}</TableCell>

      {/* Sessions */}
      <TableCell>
        {sessions.length > 0 ? (
          <Link
            to="/project/$projectId/sessions/$sessionId"
            params={{ projectId, sessionId: sessions[0].id }}
            onClick={(e) => e.stopPropagation()}
            className="group/link"
          >
            <span className="text-xs text-primary group-hover/link:underline tabular-nums">
              {sessions.length} run{sessions.length > 1 ? "s" : ""}
            </span>
          </Link>
        ) : (
          <span className="text-xs text-muted-foreground/40">-</span>
        )}
      </TableCell>

      {/* Health */}
      <TableCell className="hidden sm:table-cell">
        <HealthDot status={health} tooltip={health.replace("_", " ")} />
      </TableCell>

      {/* Cost */}
      <TableCell className="hidden sm:table-cell">
        {f.total_cost_usd > 0 ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="text-xs text-muted-foreground font-mono tabular-nums">
                ${f.total_cost_usd.toFixed(2)}
              </span>
            </TooltipTrigger>
            {f.total_tokens > 0 && (
              <TooltipContent>
                <p className="text-xs">{formatTokens(f.total_tokens)} tokens</p>
              </TooltipContent>
            )}
          </Tooltip>
        ) : (
          <span className="text-xs text-muted-foreground/40">-</span>
        )}
      </TableCell>

      {/* Updated */}
      <TableCell className="hidden sm:table-cell">
        <span className="text-[11px] text-muted-foreground/60 tabular-nums">
          {formatTimeAgo(f.updated_at || f.created_at)}
        </span>
      </TableCell>

      {/* Run */}
      <TableCell>
        <Button
          size="sm"
          variant="ghost"
          onClick={(e) => onRunClick(e, f)}
          className="h-7 w-7 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <Play className="h-3.5 w-3.5" />
        </Button>
      </TableCell>
    </TableRow>
  );
}

function buildProgressCell(sessions: SessionListEntry[]): React.ReactNode {
  if (sessions.length === 0) {
    return <span className="text-xs text-muted-foreground/40">-</span>;
  }

  const latest = sessions[0];
  const nodes = (latest as Record<string, unknown>).node_instances as
    | Record<string, { state: string }>
    | undefined;

  if (!nodes || Object.keys(nodes).length === 0) {
    return (
      <span className="text-xs text-muted-foreground/60">
        {sessions.length} session{sessions.length > 1 ? "s" : ""}
      </span>
    );
  }

  const entries = Object.values(nodes);
  const total = entries.length;
  const completed = entries.filter(
    (n) => n.state === "task_completed" || n.state === "gate_approved",
  ).length;
  const failed = entries.filter(
    (n) => n.state === "task_failed" || n.state === "gate_rejected",
  ).length;
  const running = entries.filter(
    (n) => n.state === "task_running" || n.state === "gate_waiting",
  ).length;
  const pending = total - completed - running - failed;

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
          fraction: pending / total,
          color: "bg-muted-foreground/20",
          label: `${pending} pending`,
        },
      ]}
    />
  );
}

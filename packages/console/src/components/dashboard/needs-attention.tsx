/**
 * NeedsAttention — inline attention chips, no card wrapper.
 * Auto-hides when nothing needs attention.
 */

import { Link } from "@tanstack/react-router";
import { Skeleton } from "@/components/ui/skeleton";
import { ShieldAlert, AlertTriangle, XCircle, RefreshCw } from "lucide-react";
import type { DashboardOverview } from "@/types/api";
import { humanize, type FeatureStats } from "./helpers";

interface NeedsAttentionProps {
  data: DashboardOverview | undefined;
  projectId: string;
  isLoading: boolean;
}

export function NeedsAttention({
  data,
  projectId,
  isLoading,
}: NeedsAttentionProps) {
  if (isLoading) {
    return <Skeleton className="h-7 w-64" />;
  }

  const pendingGates = data?.pending_gates ?? [];
  const stats: FeatureStats = data?.stats?.features || {
    total: 0,
    backlog: 0,
    planned: 0,
    in_progress: 0,
    review: 0,
    blocked: 0,
    done: 0,
    failed: 0,
    total_cost: 0,
    total_tokens: 0,
  };
  const recovery = data?.recovery;

  const items: Array<{
    icon: typeof ShieldAlert;
    color: string;
    label: string;
    detail: string;
    href?: { to: string; params: Record<string, string> };
  }> = [];

  if (pendingGates.length > 0) {
    items.push({
      icon: ShieldAlert,
      color: "text-amber-600 dark:text-amber-400",
      label: `${pendingGates.length} pending gate${pendingGates.length > 1 ? "s" : ""}`,
      detail: pendingGates[0] ? humanize(pendingGates[0].node_id) : "",
      href: {
        to: "/project/$projectId/sessions/$sessionId",
        params: { projectId, sessionId: pendingGates[0]?.session_id ?? "" },
      },
    });
  }

  if (stats.blocked > 0) {
    items.push({
      icon: AlertTriangle,
      color: "text-red-600 dark:text-red-400",
      label: `${stats.blocked} blocked`,
      detail: "",
      href: { to: "/project/$projectId/features", params: { projectId } },
    });
  }

  if (stats.failed > 0) {
    items.push({
      icon: XCircle,
      color: "text-red-600 dark:text-red-400",
      label: `${stats.failed} failed`,
      detail: "",
      href: { to: "/project/$projectId/features", params: { projectId } },
    });
  }

  if (recovery && recovery.escalated > 0) {
    items.push({
      icon: RefreshCw,
      color: "text-orange-600 dark:text-orange-400",
      label: `${recovery.escalated} escalated`,
      detail: "",
    });
  }

  if (items.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 py-2">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground mr-1">
        Attention
      </span>
      {items.map((item, i) => {
        const ItemIcon = item.icon;
        const chip = (
          <span className="inline-flex items-center gap-1.5 text-xs hover:opacity-70 transition-opacity cursor-pointer">
            <ItemIcon className={`h-3 w-3 shrink-0 ${item.color}`} />
            <span className="font-medium">{item.label}</span>
            {item.detail && (
              <span className="text-muted-foreground">{item.detail}</span>
            )}
          </span>
        );
        return item.href ? (
          <Link
            key={i}
            to={item.href.to as any}
            params={item.href.params as any}
          >
            {chip}
          </Link>
        ) : (
          <span key={i}>{chip}</span>
        );
      })}
    </div>
  );
}

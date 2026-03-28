"use client";

import { cn } from "@/lib/utils";
import { formatTimeAgo } from "@/lib/format-utils";
import type { Event } from "@/types/api";
import {
  Circle,
  Play,
  Shield,
  FileText,
  RefreshCw,
  CheckSquare,
  Activity,
  XCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface ActivityTimelineProps {
  events: Event[];
  className?: string;
}

interface TimeGroup {
  label: string;
  timestamp: string;
  events: Event[];
}

function getEventIcon(type: string): { icon: LucideIcon; color: string } {
  if (type.startsWith("session_")) {
    return { icon: Circle, color: "text-blue-500" };
  }
  if (type.startsWith("task_")) {
    const failed = type.includes("failed") || type.includes("blocked");
    return { icon: failed ? XCircle : Play, color: failed ? "text-red-500" : "text-green-500" };
  }
  if (type.startsWith("gate_")) {
    return { icon: Shield, color: "text-amber-500" };
  }
  if (type.startsWith("artifact_") || type.startsWith("frozen_artifact_")) {
    return { icon: FileText, color: "text-violet-500" };
  }
  if (type.startsWith("recovery_")) {
    return { icon: RefreshCw, color: "text-orange-500" };
  }
  if (type.startsWith("contract_")) {
    const color = type.includes("passed")
      ? "text-green-500"
      : type.includes("violation")
        ? "text-red-500"
        : "text-amber-500";
    return { icon: CheckSquare, color };
  }
  return { icon: Activity, color: "text-muted-foreground" };
}

function formatEventDescription(event: Event): string {
  const label = event.type.replace(/_/g, " ");
  const parts = [label];

  if (event.node_id) {
    parts.push(`on ${event.node_id}`);
  }
  if (event.artifact_id) {
    parts.push(`(${event.artifact_id})`);
  }

  return parts.join(" ");
}

function groupByTime(events: Event[]): TimeGroup[] {
  const sorted = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  const groups: TimeGroup[] = [];
  const FIVE_MIN = 5 * 60 * 1000;

  for (const event of sorted) {
    const ts = new Date(event.timestamp).getTime();
    const last = groups[groups.length - 1];

    if (last && ts - new Date(last.timestamp).getTime() < FIVE_MIN) {
      last.events.push(event);
    } else {
      groups.push({
        label: formatTimeAgo(event.timestamp),
        timestamp: event.timestamp,
        events: [event],
      });
    }
  }

  return groups;
}

export function ActivityTimeline({ events, className }: ActivityTimelineProps) {
  if (events.length === 0) {
    return (
      <div className={cn("text-xs text-muted-foreground py-4 text-center", className)}>
        No events recorded.
      </div>
    );
  }

  const groups = groupByTime(events);

  return (
    <div className={cn("space-y-4", className)}>
      {groups.map((group, gi) => (
        <div key={gi}>
          <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide mb-1.5">
            {group.label}
          </div>
          <div className="relative pl-4 border-l border-border space-y-2">
            {group.events.map((event) => {
              const { icon: Icon, color } = getEventIcon(event.type);
              return (
                <div key={event.id} className="relative flex items-start gap-2 text-xs">
                  <div
                    className={cn(
                      "absolute -left-[calc(0.5rem+1px)] top-0.5 rounded-full bg-background p-0.5",
                      color
                    )}
                  >
                    <Icon className="h-3 w-3" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm text-foreground">
                      {formatEventDescription(event)}
                    </span>
                  </div>
                  <time className="text-[10px] text-muted-foreground whitespace-nowrap">
                    {new Date(event.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </time>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronRight, ArrowDown } from "lucide-react";
import { formatTimeAgo } from "@/lib/format-utils";
import type { Event } from "@/types/api";

const TYPE_COLORS: Record<string, string> = {
  // info-level
  session_created: "text-muted-foreground",
  session_started: "text-muted-foreground",
  session_completed: "text-muted-foreground",
  session_paused: "text-muted-foreground",
  session_resumed: "text-muted-foreground",
  task_started: "text-muted-foreground",
  task_completed: "text-muted-foreground",
  checkpoint_saved: "text-muted-foreground",
  // warn
  session_reclaimed: "text-amber-600 dark:text-amber-400",
  contract_warning: "text-amber-600 dark:text-amber-400",
  task_blocked: "text-amber-600 dark:text-amber-400",
  loop_max_reached: "text-amber-600 dark:text-amber-400",
  // error
  session_failed: "text-red-600 dark:text-red-400",
  task_failed: "text-red-600 dark:text-red-400",
  error: "text-red-600 dark:text-red-400",
  contract_violation: "text-red-600 dark:text-red-400",
  sdk_error: "text-red-600 dark:text-red-400",
  recovery_failed: "text-red-600 dark:text-red-400",
  // tool
  sdk_tool_call_started: "text-blue-600 dark:text-blue-400",
  sdk_tool_call_completed: "text-blue-600 dark:text-blue-400",
  // thinking
  sdk_thinking_started: "text-violet-600 dark:text-violet-400",
  sdk_thinking_completed: "text-violet-600 dark:text-violet-400",
};

function getColorClass(type: string): string {
  return TYPE_COLORS[type] ?? "text-muted-foreground";
}

function isThinkingEvent(type: string): boolean {
  return type === "sdk_thinking_started" || type === "sdk_thinking_completed";
}

function ThinkingBlock({ event }: { event: Event }) {
  const [open, setOpen] = React.useState(false);
  const content =
    typeof event.data?.content === "string" ? event.data.content : null;

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex items-center gap-1 text-xs text-violet-600 hover:underline dark:text-violet-400">
        <ChevronRight
          className={cn("h-3 w-3 transition-transform", open && "rotate-90")}
        />
        Thinking
      </CollapsibleTrigger>
      <CollapsibleContent>
        {content ? (
          <pre className="mt-1 whitespace-pre-wrap rounded bg-violet-50 p-2 text-xs text-violet-800 dark:bg-violet-950 dark:text-violet-200">
            {content}
          </pre>
        ) : (
          <span className="text-xs text-muted-foreground">
            (no content captured)
          </span>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}

function LogEntry({ event }: { event: Event }) {
  if (isThinkingEvent(event.type)) {
    return <ThinkingBlock event={event} />;
  }

  const message =
    typeof event.data?.message === "string"
      ? event.data.message
      : typeof event.data?.summary === "string"
        ? event.data.summary
        : event.type.replace(/_/g, " ");

  return (
    <div className="flex items-start gap-2 text-xs leading-5">
      <span className="shrink-0 text-muted-foreground">
        {formatTimeAgo(event.timestamp)}
      </span>
      <span className={cn("break-all", getColorClass(event.type))}>
        {message}
      </span>
    </div>
  );
}

export function LiveLogFeed({
  events,
  className,
}: {
  events: Event[];
  className?: string;
}) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = React.useState(true);
  const [showButton, setShowButton] = React.useState(false);

  const handleScroll = React.useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setAutoScroll(nearBottom);
    setShowButton(!nearBottom);
  }, []);

  React.useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events.length, autoScroll]);

  const scrollToBottom = React.useCallback(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
      setAutoScroll(true);
      setShowButton(false);
    }
  }, []);

  return (
    <div className={cn("relative", className)}>
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex h-full flex-col gap-1 overflow-auto p-3"
        data-testid="live-log-feed"
      >
        {events.length === 0 ? (
          <span className="text-xs text-muted-foreground">
            No events yet
          </span>
        ) : (
          events.map((event) => <LogEntry key={event.id} event={event} />)
        )}
      </div>

      {showButton && (
        <Button
          size="sm"
          variant="secondary"
          onClick={scrollToBottom}
          className="absolute bottom-3 left-1/2 -translate-x-1/2 gap-1 text-xs shadow"
          aria-label="Scroll to bottom"
        >
          <ArrowDown className="h-3 w-3" />
          Scroll to bottom
        </Button>
      )}
    </div>
  );
}

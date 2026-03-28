/**
 * Kanban column — Linear-inspired container with colored accent and scrollable items.
 */

import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { KanbanCard } from "./KanbanCard";
import type { KanbanColumnProps } from "@/types/dnd";
import type { SessionListEntry, FeatureStatus } from "@/types/api";

interface KanbanColumnPropsWithSessions extends KanbanColumnProps {
  sessionsByFeature: Map<string, SessionListEntry[]>;
  projectId: string;
}

const COLUMN_ACCENT: Record<FeatureStatus, { bar: string; dot: string }> = {
  backlog: { bar: "bg-gray-400", dot: "bg-gray-400" },
  planned: { bar: "bg-blue-400", dot: "bg-blue-400" },
  in_progress: { bar: "bg-amber-400", dot: "bg-amber-400" },
  review: { bar: "bg-indigo-400", dot: "bg-indigo-400" },
  blocked: { bar: "bg-red-400", dot: "bg-red-400" },
  done: { bar: "bg-green-400", dot: "bg-green-400" },
  failed: { bar: "bg-red-600", dot: "bg-red-600" },
};

export function KanbanColumn({
  column,
  sessionsByFeature,
  projectId,
  onFeatureClick,
  onRunClick,
}: KanbanColumnPropsWithSessions) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
    data: { column },
  });

  const accent = COLUMN_ACCENT[column.id] ?? COLUMN_ACCENT.backlog;

  return (
    <div
      className={`w-72 sm:w-80 rounded-lg border bg-muted/30 transition-all flex flex-col ${
        isOver
          ? "ring-2 ring-primary/40 bg-primary/5 border-primary/30"
          : "border-border/50"
      }`}
    >
      {/* Color accent */}
      <div className={`h-0.5 rounded-t-lg ${accent.bar}`} />

      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5">
        <span className={`w-2 h-2 rounded-full ${accent.dot}`} />
        <h3 className="font-medium text-xs uppercase tracking-wider text-muted-foreground flex-1">
          {column.title}
        </h3>
        <span className="text-[11px] text-muted-foreground/60 tabular-nums bg-muted rounded-full px-2 py-0.5">
          {column.features.length}
        </span>
      </div>

      {/* Items */}
      <div
        ref={setNodeRef}
        className="flex-1 min-h-16 overflow-y-auto px-0.5 pb-1.5"
        style={{ maxHeight: "calc(100vh - 280px)" }}
      >
        <SortableContext
          items={column.features.map((f) => f.id)}
          strategy={verticalListSortingStrategy}
        >
          {column.features.length > 0 ? (
            column.features.map((feature) => (
              <KanbanCard
                key={feature.id}
                feature={feature}
                sessionsByFeature={sessionsByFeature}
                projectId={projectId}
                onFeatureClick={onFeatureClick}
                onRunClick={onRunClick}
              />
            ))
          ) : (
            <div className="flex items-center justify-center h-20 text-muted-foreground/40 text-xs">
              Drop here
            </div>
          )}
        </SortableContext>
      </div>
    </div>
  );
}

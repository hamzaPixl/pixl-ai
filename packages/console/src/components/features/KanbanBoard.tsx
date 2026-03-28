/**
 * Kanban board — horizontally scrollable columns with drag-and-drop.
 * Empty columns collapse to narrow vertical strips.
 */

import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import { useState } from "react";
import { useDroppable } from "@dnd-kit/core";
import { KanbanColumn } from "./KanbanColumn";
import { KanbanCard } from "./KanbanCard";
import { useKanbanDnd } from "@/hooks/features/use-kanban-dnd";
import type { KanbanBoardProps, DroppableColumn } from "@/types/dnd";
import type { SessionListEntry, Feature } from "@/types/api";

interface KanbanBoardPropsWithSessions extends KanbanBoardProps {
  sessionsByFeature: Map<string, SessionListEntry[]>;
}

/** Narrow collapsed column for empty statuses — expands on drag over */
function CollapsedColumn({ column }: { column: DroppableColumn }) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
    data: { column },
  });

  return (
    <div
      ref={setNodeRef}
      className={`flex-shrink-0 rounded-lg border transition-all duration-200 flex items-center justify-center ${
        isOver
          ? "w-72 sm:w-80 ring-2 ring-primary/40 bg-primary/5 border-primary/30"
          : "w-10 bg-muted/10 border-border/30 hover:bg-muted/20"
      }`}
      style={{ minHeight: 120 }}
    >
      <span className="text-[10px] text-muted-foreground/40 font-medium uppercase tracking-wider whitespace-nowrap [writing-mode:vertical-lr] rotate-180">
        {column.title}
      </span>
    </div>
  );
}

export function KanbanBoard({
  features,
  projectId,
  onFeatureStatusUpdate,
  onFeatureClick,
  onRunClick,
  sessionsByFeature,
}: KanbanBoardPropsWithSessions) {
  const [activeFeature, setActiveFeature] = useState<Feature | null>(null);

  const { columns, handleDragEnd } = useKanbanDnd({
    features,
    onFeatureStatusUpdate,
  });

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  return (
    <div className="w-full -mx-1">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={(event) => {
          setActiveFeature(
            (event.active.data.current as { feature: Feature })?.feature ??
              null,
          );
        }}
        onDragEnd={(event) => {
          handleDragEnd(event);
          setActiveFeature(null);
        }}
      >
        <div className="flex gap-2 overflow-x-auto pb-4 px-1 scrollbar-thin">
          {columns.map((column) => (
            <div key={column.id} className="flex-shrink-0">
              {column.features.length === 0 ? (
                <CollapsedColumn column={column} />
              ) : (
                <KanbanColumn
                  column={column}
                  sessionsByFeature={sessionsByFeature}
                  projectId={projectId}
                  onFeatureClick={onFeatureClick}
                  onRunClick={onRunClick}
                />
              )}
            </div>
          ))}
        </div>

        <DragOverlay dropAnimation={{ duration: 200, easing: "ease-out" }}>
          {activeFeature ? (
            <KanbanCard
              feature={activeFeature}
              sessionsByFeature={sessionsByFeature}
              projectId={projectId}
              isDragOverlay
              onFeatureClick={onFeatureClick}
              onRunClick={onRunClick}
            />
          ) : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
}

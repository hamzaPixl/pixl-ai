/**
 * Hook for managing Kanban board drag and drop functionality
 */

import { useMemo } from 'react';
import { DragEndEvent } from '@dnd-kit/core';
import type { Feature, FeatureStatus } from '@/types/api';
import type { DroppableColumn } from '@/types/dnd';

// Status configuration with display names
const STATUS_CONFIG: Record<FeatureStatus, { title: string; order: number }> = {
  backlog: { title: 'Backlog', order: 0 },
  planned: { title: 'Planned', order: 1 },
  in_progress: { title: 'In Progress', order: 2 },
  review: { title: 'Review', order: 3 },
  blocked: { title: 'Blocked', order: 4 },
  done: { title: 'Done', order: 5 },
  failed: { title: 'Failed', order: 6 },
};

export interface UseKanbanDndProps {
  features: Feature[];
  onFeatureStatusUpdate: (featureId: string, newStatus: FeatureStatus) => void;
}

export interface UseKanbanDndReturn {
  columns: DroppableColumn[];
  handleDragEnd: (event: DragEndEvent) => void;
  isValidTransition: (fromStatus: FeatureStatus, toStatus: FeatureStatus) => boolean;
}

export function useKanbanDnd({ features, onFeatureStatusUpdate }: UseKanbanDndProps): UseKanbanDndReturn {

  // Group features by status into columns
  const columns = useMemo((): DroppableColumn[] => {
    const featuresByStatus = new Map<FeatureStatus, Feature[]>();

    Object.keys(STATUS_CONFIG).forEach(status => {
      featuresByStatus.set(status as FeatureStatus, []);
    });

    // Group features by their current status
    features.forEach(feature => {
      const statusFeatures = featuresByStatus.get(feature.status) || [];
      statusFeatures.push(feature);
      featuresByStatus.set(feature.status, statusFeatures);
    });

    return Object.entries(STATUS_CONFIG)
      .sort(([, a], [, b]) => a.order - b.order)
      .map(([status, config]) => ({
        id: status as FeatureStatus,
        title: config.title,
        features: featuresByStatus.get(status as FeatureStatus) || [],
      }));
  }, [features]);

  const isValidTransition = (fromStatus: FeatureStatus, toStatus: FeatureStatus): boolean => {
    // Allow moving to any status except for some business rules
    if (fromStatus === toStatus) return false;

    // Can't move to 'failed' status manually (should be set by system) - but check exists first
    if (toStatus === 'failed' as FeatureStatus) return false;

    // Can move from any status to blocked
    if (toStatus === 'blocked') return true;

    // Can move from blocked to any other status except failed
    if (fromStatus === 'blocked' && toStatus !== ('failed' as FeatureStatus)) return true;

    // Normal forward/backward progression
    const fromOrder = STATUS_CONFIG[fromStatus]?.order ?? -1;
    const toOrder = STATUS_CONFIG[toStatus]?.order ?? -1;

    // Allow moving forward or backward in the workflow
    return fromOrder !== toOrder;
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (!over) {
        return;
    }

    const activeFeature = active.data.current?.feature as Feature;
    const overColumn = over.data?.current?.column as DroppableColumn;

    if (!activeFeature || !overColumn) {
        return;
    }

    const newStatus = overColumn.id;
    const currentStatus = activeFeature.status;

    if (!isValidTransition(currentStatus, newStatus)) {
        return;
    }

    // Only update if status actually changed
    if (currentStatus !== newStatus) {
      onFeatureStatusUpdate(activeFeature.id, newStatus);
    }

  };

  return {
    columns,
    handleDragEnd,
    isValidTransition,
  };
}
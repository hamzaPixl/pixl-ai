/**
 * Drag and Drop types for Kanban board functionality
 */

import type { Feature, FeatureStatus } from '@/types/api';

export interface DroppableColumn {
  id: FeatureStatus;
  title: string;
  features: Feature[];
}

export interface DragEndEvent {
  active: {
    id: string;
    data: {
      current: {
        feature: Feature;
      };
    };
  };
  over: {
    id: string;
    data?: {
      current?: {
        column: DroppableColumn;
      };
    };
  } | null;
}

export interface KanbanBoardProps {
  features: Feature[];
  projectId: string;
  onFeatureStatusUpdate: (featureId: string, newStatus: FeatureStatus) => void;
  onFeatureClick?: (feature: Feature) => void;
  onRunClick?: (e: React.MouseEvent, feature: Feature) => void;
}

export interface KanbanColumnProps {
  column: DroppableColumn;
  projectId: string;
  onFeatureClick?: (feature: Feature) => void;
  onRunClick?: (e: React.MouseEvent, feature: Feature) => void;
}

export interface KanbanCardProps {
  feature: Feature;
  sessionsByFeature: Map<string, { id: string; status?: string }[]>;
  projectId: string;
  isDragOverlay?: boolean;
  onFeatureClick?: (feature: Feature) => void;
  onRunClick?: (e: React.MouseEvent, feature: Feature) => void;
}

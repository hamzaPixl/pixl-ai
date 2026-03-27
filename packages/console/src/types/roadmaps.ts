import type { RoadmapStatus, MilestoneStatus } from "./enums";

export interface Milestone {
  id: string;
  title: string;
  description: string;
  status: MilestoneStatus;

  // Linked entities
  epic_ids: string[];
  feature_ids: string[];

  // Success criteria
  success_criteria: string[];

  // Timestamps
  created_at: string;
  started_at: string | null;
  completed_at: string | null;

  // Tracking
  notes: string[];
}

export interface Roadmap {
  id: string; // roadmap-XXX
  title: string;
  original_prompt: string;
  epic_ids: string[];
  milestones: Milestone[];
  status: RoadmapStatus;

  // Timestamps
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;

  // Tracking
  notes: string[];
}

export interface CreateRoadmapRequest {
  title: string;
  original_prompt?: string;
}

export interface UpdateRoadmapRequest {
  title?: string;
  original_prompt?: string;
}

export interface CreateMilestoneRequest {
  name: string;
  target_date?: string | null;
  sort_order?: number;
}

// Roadmap Rollup (used by views)

export interface RoadmapRollup {
  id: string;
  title: string;
  status: RoadmapStatus;
  created_at: string | null;
  completed_at: string | null;
  epic_count: number;
  feature_count: number;
  features_done: number;
  features_total: number;
  features_in_progress: number;
  progress_pct: number;
  top_blockers: Array<{
    id: string;
    title: string;
    blocked_reason: string | null;
  }>;
  confidence: number;
}

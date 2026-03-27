import type { WorkItemType } from "./enums";

export interface ListParams extends Record<
  string,
  string | number | boolean | undefined
> {
  limit?: number;
  offset?: number;
  status?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
  [key: string]: string | number | boolean | undefined;
}

export interface WorkItem {
  id: string;
  title: string;
  type: WorkItemType;
  status: string;
  description?: string;
  created_at: string;
  updated_at?: string | null;
  epic_id?: string | null;
  roadmap_id?: string | null;
  [key: string]: unknown;
}

export interface ApiResponse<T> {
  data: T;
  error?: string;
}

export interface ApiError {
  detail: string;
  status?: number;
}

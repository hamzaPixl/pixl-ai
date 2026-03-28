// Project Types

export interface Project {
  project_id: string;
  project_name: string;
  project_root: string | null;
  storage_dir: string;
  db_path: string | null;
  storage_mode: string | null;
  last_used_at: number | null;
  [key: string]: unknown;
}

export interface CreateProjectRequest {
  name: string;
  description: string;
  project_root?: string | null;
}

export interface InitProjectResponse {
  session_id: string;
  status: string;
}

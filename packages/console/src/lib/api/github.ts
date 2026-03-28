import { get, post, del } from "./core";

export interface GitHubStatus {
  connected: boolean;
  github_username: string | null;
}

export interface GitHubRepo {
  full_name: string;
  name: string;
  private: boolean;
  clone_url: string;
  default_branch: string;
  description: string | null;
}

export interface LinkedRepo {
  project_id: string;
  workspace_id: string;
  repo_full_name: string;
  repo_url: string;
  default_branch: string;
  auto_push: number;
  linked_at: string;
}

export const github = {
  status: (): Promise<GitHubStatus> => get("/github/status"),
  repos: (params?: {
    page?: number;
    per_page?: number;
  }): Promise<GitHubRepo[]> => get("/github/repos", params),
  createRepo: (body: {
    name: string;
    description?: string;
    private?: boolean;
  }): Promise<GitHubRepo> => post("/github/repos", body),
  disconnect: (): Promise<{ disconnected: boolean }> => del("/github/disconnect"),
};

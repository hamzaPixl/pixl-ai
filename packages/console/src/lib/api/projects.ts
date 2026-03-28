import type { Project } from "@/types/api";
import type { LinkedRepo } from "./github";
import { get, post, patch, del } from "./core";

export const projects = {
  list: (): Promise<Project[]> => get("/projects"),

  get: (id: string): Promise<Project> => get(`/projects/${id}`),

  create: (data: {
    name: string;
    description: string;
    project_root: string | null;
    github_repo?: string | null;
  }): Promise<Project> => post("/projects", data),

  init: (
    projectId: string,
    data: { description: string },
  ): Promise<{ session_id: string; status: string }> =>
    post(`/projects/${projectId}/init`, data),

  delete: (id: string): Promise<void> => del(`/projects/${id}`),
};

export interface EnvVar {
  key: string;
  value: string;
  is_secret: boolean;
  created_at: string;
  updated_at: string;
}

export interface GeneralSettings {
  project_id: string;
  name: string;
  description: string;
  project_root: string | null;
}

export const projectSettings = {
  // Env vars
  listEnvVars: (projectId: string): Promise<EnvVar[]> =>
    get(`/projects/${projectId}/settings/env-vars`),
  upsertEnvVar: (
    projectId: string,
    data: { key: string; value: string; is_secret?: boolean },
  ): Promise<{ key: string; is_secret: boolean }> =>
    post(`/projects/${projectId}/settings/env-vars`, data),
  deleteEnvVar: (projectId: string, key: string): Promise<{ deleted: boolean }> =>
    del(`/projects/${projectId}/settings/env-vars/${encodeURIComponent(key)}`),

  // GitHub
  getLinkedRepo: (projectId: string): Promise<LinkedRepo | null> =>
    get(`/projects/${projectId}/settings/github`),
  linkRepo: (
    projectId: string,
    data: { repo_full_name: string; auto_push?: boolean },
  ): Promise<LinkedRepo> =>
    post(`/projects/${projectId}/settings/github/link`, data),
  unlinkRepo: (projectId: string): Promise<{ unlinked: boolean }> =>
    del(`/projects/${projectId}/settings/github/link`),

  // General
  getGeneral: (projectId: string): Promise<GeneralSettings> =>
    get(`/projects/${projectId}/settings/general`),
  updateGeneral: (
    projectId: string,
    data: { name?: string; description?: string },
  ): Promise<GeneralSettings> =>
    patch(`/projects/${projectId}/settings/general`, data),
};

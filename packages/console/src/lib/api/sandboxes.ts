/**
 * Sandbox API client — Cloudflare Workers sandbox management.
 */

import { get, post, del } from "./core";

export interface SandboxInfo {
  id: string;
  status: string;
  created_at: string;
  project_id?: string;
}

export interface ExecResult {
  exit_code: number;
  stdout: string;
  stderr: string;
}

export interface WorkflowRunResult {
  session_id: string;
  status: string;
}

export const sandboxes = {
  /** Create a new sandbox. */
  create(data: { project_id?: string }): Promise<SandboxInfo> {
    return post<SandboxInfo>("/sandboxes", data);
  },

  /** List all sandboxes. */
  list(): Promise<SandboxInfo[]> {
    return get<SandboxInfo[]>("/sandboxes");
  },

  /** Get sandbox status by ID. */
  get(sandboxId: string): Promise<SandboxInfo> {
    return get<SandboxInfo>(`/sandboxes/${sandboxId}`);
  },

  /** Delete a sandbox by ID. */
  destroy(sandboxId: string): Promise<void> {
    return del<void>(`/sandboxes/${sandboxId}`);
  },

  /** Execute a command in a sandbox. */
  exec(sandboxId: string, command: string): Promise<ExecResult> {
    return post<ExecResult>(`/sandboxes/${sandboxId}/exec`, { command });
  },

  /** Run a workflow in a sandbox. */
  runWorkflow(
    sandboxId: string,
    data: { workflow?: string; prompt?: string },
  ): Promise<WorkflowRunResult> {
    return post<WorkflowRunResult>(`/sandboxes/${sandboxId}/workflow`, data);
  },
};

import type { Sandbox as SandboxDO } from "@cloudflare/sandbox";

export interface Env {
  Sandbox: DurableObjectNamespace<SandboxDO>;
  ANTHROPIC_API_KEY: string;
  OPENAI_API_KEY?: string;
  SANDBOX_API_KEY?: string;   // Legacy — optional fallback
  JWT_SECRET?: string;         // HS256 secret for JWT verification
  ALLOWED_ORIGINS?: string;
}

export interface SandboxCreateRequest {
  projectId: string;
  repoUrl?: string;
  branch?: string;
  envVars?: Record<string, string>;
  keepAlive?: number;
}

export interface WorkflowRequest {
  prompt: string;
  workflowId?: string;
  autoApprove?: boolean;
}

export interface ExecRequest {
  command: string;
  timeout?: number;
  env?: Record<string, string>;
  cwd?: string;
}

export interface FileWriteRequest {
  path: string;
  content: string;
}

export interface ProcessStartRequest {
  command: string;
  cwd?: string;
  env?: Record<string, string>;
}

export interface GitConfigRequest {
  userName?: string;
  userEmail?: string;
  remoteUrl?: string;
}

export interface SessionExportBundle {
  session: Record<string, unknown>;
  node_instances: Record<string, unknown>[];
  events: Record<string, unknown>[];
  snapshot: string | null;
  exported_at: string;
  sandbox_id: string;
}

export interface SessionImportRequest {
  session: Record<string, unknown>;
  node_instances?: Record<string, unknown>[];
  events?: Record<string, unknown>[];
  snapshot?: string | null;
}

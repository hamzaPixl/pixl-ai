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

// --- Session import bundle validation ---

export interface ValidationError {
  readonly field: string;
  readonly message: string;
}

/**
 * Validate a session import bundle before executing the import script.
 * Returns an array of validation errors (empty = valid).
 */
export function validateSessionImportBundle(
  body: unknown,
): readonly ValidationError[] {
  const errors: ValidationError[] = [];

  if (body === null || typeof body !== "object") {
    return [{ field: "body", message: "Request body must be a JSON object" }];
  }

  const bundle = body as Record<string, unknown>;

  // --- session (required object with required fields) ---
  if (!bundle.session || typeof bundle.session !== "object" || Array.isArray(bundle.session)) {
    errors.push({ field: "session", message: "session must be a non-null object" });
  } else {
    const session = bundle.session as Record<string, unknown>;
    if (!session.id || typeof session.id !== "string") {
      errors.push({ field: "session.id", message: "session.id must be a non-empty string" });
    }
    if (!session.feature_id || typeof session.feature_id !== "string") {
      errors.push({ field: "session.feature_id", message: "session.feature_id must be a non-empty string" });
    }
    if (session.snapshot_hash !== undefined && session.snapshot_hash !== null && typeof session.snapshot_hash !== "string") {
      errors.push({ field: "session.snapshot_hash", message: "session.snapshot_hash must be a string or null" });
    }
    if (session.node_instances !== undefined && session.node_instances !== null && typeof session.node_instances !== "object") {
      errors.push({ field: "session.node_instances", message: "session.node_instances must be an object or null" });
    }
  }

  // --- events (optional array, but if present each item must have id, event_type, session_id) ---
  if (bundle.events !== undefined) {
    if (!Array.isArray(bundle.events)) {
      errors.push({ field: "events", message: "events must be an array" });
    } else {
      for (let i = 0; i < bundle.events.length; i++) {
        const ev = bundle.events[i] as Record<string, unknown> | null;
        if (!ev || typeof ev !== "object" || Array.isArray(ev)) {
          errors.push({ field: `events[${i}]`, message: "each event must be a non-null object" });
          continue;
        }
        if (!ev.event_type || typeof ev.event_type !== "string") {
          errors.push({
            field: `events[${i}].event_type`,
            message: "event_type must be a non-empty string",
          });
        }
        if (ev.session_id !== undefined && ev.session_id !== null && typeof ev.session_id !== "string") {
          errors.push({
            field: `events[${i}].session_id`,
            message: "session_id must be a string if provided",
          });
        }
      }
    }
  }

  // --- node_instances (optional array) ---
  if (bundle.node_instances !== undefined) {
    if (!Array.isArray(bundle.node_instances)) {
      errors.push({ field: "node_instances", message: "node_instances must be an array" });
    } else {
      for (let i = 0; i < bundle.node_instances.length; i++) {
        const ni = bundle.node_instances[i] as Record<string, unknown> | null;
        if (!ni || typeof ni !== "object" || Array.isArray(ni)) {
          errors.push({ field: `node_instances[${i}]`, message: "each node_instance must be a non-null object" });
          continue;
        }
        if (!ni.node_id || typeof ni.node_id !== "string") {
          errors.push({
            field: `node_instances[${i}].node_id`,
            message: "node_id must be a non-empty string",
          });
        }
      }
    }
  }

  return errors;
}

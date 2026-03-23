import { Hono } from "hono";
import { cors } from "hono/cors";
import { bodyLimit } from "hono/body-limit";
import { getSandbox } from "@cloudflare/sandbox";
import { jwtVerify, type JWTPayload } from "jose";

import type {
  Env,
  SandboxCreateRequest,
  WorkflowRequest,
  ExecRequest,
  FileWriteRequest,
  ProcessStartRequest,
  GitConfigRequest,
  SessionImportRequest,
} from "./types.js";
import {
  buildEnvVars,
  shellEscape,
  validatePath,
  getVersions,
  getGitInfo,
  getProjectInfo,
} from "./helpers.js";
import { logOperation, readUsage, timed } from "./usage.js";

type Scope = "read" | "write" | "admin";

const SCOPE_LEVEL: Record<Scope, number> = {
  read: 1,
  write: 2,
  admin: 3,
};

type AppVariables = {
  jwtPayload: JWTPayload;
  scope: Scope;
};

function isValidScope(value: unknown): value is Scope {
  return value === "read" || value === "write" || value === "admin";
}

function requireScope(
  c: { get(key: "scope"): Scope | undefined },
  required: Scope,
): boolean {
  const current = c.get("scope") ?? "admin";
  return SCOPE_LEVEL[current] >= SCOPE_LEVEL[required];
}

const app = new Hono<{ Bindings: Env; Variables: AppVariables }>();

// CORS middleware — configurable via ALLOWED_ORIGINS env var
app.use("*", async (c, next) => {
  const allowedOrigins = c.env.ALLOWED_ORIGINS;
  const origin = allowedOrigins
    ? allowedOrigins.split(",").map((o) => o.trim())
    : "*";
  const middleware = cors({ origin });
  return middleware(c, next);
});

// Body size limit: 10MB
app.use("*", bodyLimit({ maxSize: 10 * 1024 * 1024 }));

// Auth middleware — JWT preferred, static API key fallback. Skip for health check.
app.use("*", async (c, next) => {
  if (c.req.path === "/health") return next();

  const authHeader = c.req.header("Authorization");
  if (!authHeader?.startsWith("Bearer ")) {
    return c.json({ error: "unauthorized" }, 401);
  }

  const token = authHeader.slice(7);

  // Try JWT first (if JWT_SECRET is configured)
  if (c.env.JWT_SECRET) {
    try {
      const secret = new TextEncoder().encode(c.env.JWT_SECRET);
      const { payload } = await jwtVerify(token, secret, {
        algorithms: ["HS256"],
        issuer: "pixl-cli",
      });
      c.set("jwtPayload", payload);
      const scope = isValidScope(payload.scope) ? payload.scope : "admin";
      c.set("scope", scope);
      await next();
      return;
    } catch {
      // JWT verification failed — fall through to static key check
    }
  }

  // Fallback: static API key (legacy) — grants admin scope
  if (c.env.SANDBOX_API_KEY && token === c.env.SANDBOX_API_KEY) {
    c.set("scope", "admin");
    await next();
    return;
  }

  return c.json({ error: "forbidden" }, 403);
});

// Health check (no auth required)
app.get("/health", (c) => c.json({ status: "ok" }));

// Rate limiting — per-IP, 60 requests per minute
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT = 60;
const RATE_WINDOW_MS = 60_000;

app.use("/sandboxes/*", async (c, next) => {
  const ip =
    c.req.header("cf-connecting-ip") ||
    c.req.header("x-forwarded-for") ||
    "unknown";
  const now = Date.now();
  const entry = rateLimitMap.get(ip);

  if (!entry || now > entry.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_WINDOW_MS });
  } else {
    entry.count++;
    if (entry.count > RATE_LIMIT) {
      return c.json({ error: "Rate limit exceeded" }, 429);
    }
  }

  await next();
});

// Audit log for mutating operations
app.use("/sandboxes/*", async (c, next) => {
  const method = c.req.method;
  if (method === "POST" || method === "DELETE") {
    const path = new URL(c.req.url).pathname;
    const ip =
      c.req.header("cf-connecting-ip") ||
      c.req.header("x-forwarded-for") ||
      "unknown";
    console.log(
      `[audit] ${method} ${path} from=${ip} at ${new Date().toISOString()}`,
    );
  }
  await next();
});

// --- Sandbox lifecycle ---

// Create a sandbox — single-call setup: env vars, git clone/init, pixl init
app.post("/sandboxes", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const body = await c.req.json<SandboxCreateRequest>();
  if (!body.projectId) {
    return c.json({ error: "projectId is required" }, 400);
  }

  const sb = getSandbox(c.env.Sandbox, body.projectId, {
    keepAlive: body.keepAlive !== undefined ? Boolean(body.keepAlive) : undefined,
  });

  const { result, duration_ms } = await timed(async () => {
    // 1. Set env vars — split into regular vars and secrets
    //    Secrets are injected separately so they never appear in
    //    process spawn args or command-line logs.
    const { vars, secrets } = buildEnvVars(
      c.env.ANTHROPIC_API_KEY,
      c.env.OPENAI_API_KEY,
      body.envVars,
    );
    if (Object.keys(vars).length > 0) {
      await sb.setEnvVars(vars);
    }
    // Secrets set in a dedicated call — keeps them out of general env logging
    await sb.setEnvVars(secrets);

    // 2. Git setup — clone repo or init fresh
    if (body.repoUrl) {
      await sb.gitCheckout(body.repoUrl, {
        targetDir: "/workspace",
        branch: body.branch,
      });
    } else {
      const branch = (body.branch || "main").replace(/[^a-zA-Z0-9_.\-/]/g, "");
      await sb.exec(
        `cd /workspace && git init -b '${branch}'`,
      );
    }

    // 3. Initialize pixl
    const initResult = await sb.exec(
      "bash /usr/local/bin/pixl-init.sh /workspace",
    );
    if (initResult.exitCode !== 0) {
      return {
        success: false,
        error: initResult.stderr || initResult.stdout,
      };
    }

    // 4. Gather info
    const [versions, gitInfo] = await Promise.all([
      getVersions(sb),
      getGitInfo(sb),
    ]);

    return { success: true, versions, git: gitInfo };
  });

  await logOperation(sb, {
    timestamp: new Date().toISOString(),
    operation: "create",
    duration_ms,
    success: result.success,
    error: result.success ? undefined : result.error,
  });

  if (!result.success) {
    return c.json(
      { projectId: body.projectId, status: "error", error: result.error },
      500,
    );
  }

  return c.json({
    projectId: body.projectId,
    status: "ready",
    versions: result.versions,
    git: result.git,
  });
});

// Destroy a sandbox
app.delete("/sandboxes/:id", async (c) => {
  if (!requireScope(c, "admin")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  await sb.destroy();
  return c.json({ success: true });
});

// --- Status & observability ---

// Get sandbox status — versions, git info, project state, env var names
app.get("/sandboxes/:id/status", async (c) => {
  if (!requireScope(c, "read")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));

  const [versions, gitInfo, projectInfo] = await Promise.all([
    getVersions(sb),
    getGitInfo(sb),
    getProjectInfo(sb),
  ]);

  // Get env var names (no values)
  const envResult = await sb.exec("env | cut -d= -f1 | sort");
  const envKeys = envResult.stdout
    .trim()
    .split("\n")
    .filter(Boolean);

  return c.json({
    projectId: c.req.param("id"),
    status: "running",
    versions,
    git: gitInfo,
    project: projectInfo,
    envKeys,
  });
});

// Get workflow events from sandbox pixl.db
app.get("/sandboxes/:id/events", async (c) => {
  if (!requireScope(c, "read")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const limit = c.req.query("limit") || "50";
  const result = await sb.exec(`pixl events list --json --limit ${limit}`);

  if (result.exitCode !== 0) {
    return c.json({
      success: false,
      error: result.stderr || "Failed to list events",
    }, 500);
  }

  try {
    const events = JSON.parse(result.stdout);
    return c.json({ success: true, events });
  } catch {
    return c.json({ success: true, raw: result.stdout });
  }
});

// Get usage stats
app.get("/sandboxes/:id/usage", async (c) => {
  if (!requireScope(c, "read")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const usage = await readUsage(sb);
  return c.json(usage);
});

// Bulk-export all execution data for sync to parent DB
app.get("/sandboxes/:id/export", async (c) => {
  if (!requireScope(c, "read")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const id = c.req.param("id");
  const sb = getSandbox(c.env.Sandbox, id);
  const commandTimeout = 60_000;

  const { result, duration_ms } = await timed(async () => {
    const commands = [
      "pixl events list --json",
      "pixl session list --json",
      "pixl artifact list --json",
    ] as const;

    const parseOutput = (stdout: string): unknown[] => {
      try {
        const parsed = JSON.parse(stdout);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    };

    const [eventsResult, sessionsResult, artifactsResult] = await Promise.all(
      commands.map((cmd) => sb.exec(cmd, { timeout: commandTimeout })),
    );

    return {
      sandbox_id: id,
      exported_at: new Date().toISOString(),
      events: parseOutput(eventsResult.stdout),
      sessions: parseOutput(sessionsResult.stdout),
      artifacts: parseOutput(artifactsResult.stdout),
    };
  });

  await logOperation(sb, {
    timestamp: new Date().toISOString(),
    operation: "export",
    duration_ms,
    success: true,
  });

  return c.json(result);
});

// Update env vars at runtime
app.post("/sandboxes/:id/env", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const body = await c.req.json<Record<string, string>>();
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  await sb.setEnvVars(body);
  return c.json({ success: true, keys: Object.keys(body) });
});

// --- Command execution ---

// Execute a command (returns JSON)
app.post("/sandboxes/:id/exec", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const body = await c.req.json<ExecRequest>();
  if (!body.command) {
    return c.json({ error: "command is required" }, 400);
  }

  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));

  const { result, duration_ms } = await timed(async () => {
    return sb.exec(body.command, {
      timeout: body.timeout,
      env: body.env,
      cwd: body.cwd,
    });
  });

  await logOperation(sb, {
    timestamp: new Date().toISOString(),
    operation: "exec",
    duration_ms,
    success: result.exitCode === 0,
    meta: { command: body.command.slice(0, 200) },
  });

  return c.json({
    stdout: result.stdout,
    stderr: result.stderr,
    exitCode: result.exitCode,
    success: result.exitCode === 0,
  });
});

// Execute a command (returns SSE stream)
app.post("/sandboxes/:id/exec/stream", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const body = await c.req.json<ExecRequest>();
  if (!body.command) {
    return c.json({ error: "command is required" }, 400);
  }

  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const stream = await sb.execStream(body.command, {
    timeout: body.timeout,
    env: body.env,
    cwd: body.cwd,
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
});

// --- Workflow execution ---

// Run a pixl workflow (returns JSON)
app.post("/sandboxes/:id/workflow", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const body = await c.req.json<WorkflowRequest>();
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));

  const { result, duration_ms } = await timed(async () => {
    const args = ["pixl", "workflow", "run"];
    if (body.prompt) args.push("--prompt", shellEscape(body.prompt));
    if (body.workflowId) args.push("--workflow", body.workflowId);
    if (body.autoApprove) args.push("--yes");
    args.push("--json");

    return sb.exec(args.join(" "));
  });

  await logOperation(sb, {
    timestamp: new Date().toISOString(),
    operation: "workflow",
    duration_ms,
    success: result.exitCode === 0,
    meta: { workflowId: body.workflowId },
  });

  return c.json({
    stdout: result.stdout,
    stderr: result.stderr,
    exitCode: result.exitCode,
    success: result.exitCode === 0,
  });
});

// Run a pixl workflow (returns SSE stream)
app.post("/sandboxes/:id/workflow/stream", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const body = await c.req.json<WorkflowRequest>();
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));

  const args = ["pixl", "workflow", "run"];
  if (body.prompt) args.push("--prompt", shellEscape(body.prompt));
  if (body.workflowId) args.push("--workflow", body.workflowId);
  if (body.autoApprove) args.push("--yes");
  args.push("--json");

  const rawStream = await sb.execStream(args.join(" "));

  // Wrap raw SSE in structured events (GAP-07 Phase 1)
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  let lineBuffer = "";
  const structuredStream = new TransformStream<Uint8Array, Uint8Array>({
    start(controller) {
      const startEvent = JSON.stringify({ type: "status", payload: { status: "started" } });
      controller.enqueue(encoder.encode(`data: ${startEvent}\n\n`));
    },
    transform(chunk, controller) {
      lineBuffer += decoder.decode(chunk, { stream: true });
      const segments = lineBuffer.split("\n");
      lineBuffer = segments.pop()!; // Keep incomplete tail for next chunk
      for (const line of segments) {
        if (!line.trim()) continue;
        const dataMatch = line.match(/^data:\s*(.+)/);
        const raw = dataMatch ? dataMatch[1] : line;
        try {
          const parsed = JSON.parse(raw);
          const event = JSON.stringify({ type: "event", payload: parsed });
          controller.enqueue(encoder.encode(`data: ${event}\n\n`));
        } catch {
          const event = JSON.stringify({ type: "stdout", payload: { line: raw } });
          controller.enqueue(encoder.encode(`data: ${event}\n\n`));
        }
      }
    },
    flush(controller) {
      // Flush remaining buffer content
      if (lineBuffer.trim()) {
        const event = JSON.stringify({ type: "stdout", payload: { line: lineBuffer } });
        controller.enqueue(encoder.encode(`data: ${event}\n\n`));
      }
      const endEvent = JSON.stringify({ type: "status", payload: { status: "complete" } });
      controller.enqueue(encoder.encode(`data: ${endEvent}\n\n`));
    },
  });

  return new Response(rawStream.pipeThrough(structuredStream), {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
});

// Cancel a running workflow (sends SIGINT for graceful shutdown)
app.post("/sandboxes/:id/workflow/cancel", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));

  const { result, duration_ms } = await timed(async () => {
    return sb.exec("kill -SIGINT $(pgrep -f 'pixl workflow run')");
  });

  const success = result.exitCode === 0;

  await logOperation(sb, {
    timestamp: new Date().toISOString(),
    operation: "workflow_cancel",
    duration_ms,
    success,
    error: success ? undefined : result.stderr || undefined,
  });

  return c.json({
    success,
    message: success
      ? "Workflow cancellation signal sent"
      : "No running workflow found or cancel failed",
  });
});

// --- Sessions ---

// List workflow sessions
app.get("/sandboxes/:id/sessions", async (c) => {
  if (!requireScope(c, "read")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const result = await sb.exec("pixl session list --json");

  if (result.exitCode !== 0) {
    return c.json({
      success: false,
      error: result.stderr || "Failed to list sessions",
    }, 500);
  }

  try {
    const sessions = JSON.parse(result.stdout);
    return c.json({ success: true, sessions });
  } catch {
    return c.json({ success: true, raw: result.stdout });
  }
});

// Export a single session as a portable JSON bundle (for cross-sandbox migration)
app.get("/sandboxes/:id/sessions/:sessionId/export", async (c) => {
  if (!requireScope(c, "read")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sandboxId = c.req.param("id");
  const sessionId = c.req.param("sessionId");
  const sb = getSandbox(c.env.Sandbox, sandboxId);
  const commandTimeout = 30_000;

  const { result, duration_ms } = await timed(async () => {
    const sessionResult = await sb.exec(
      `pixl session get ${sessionId} --json`,
      { timeout: commandTimeout },
    );

    if (sessionResult.exitCode !== 0) {
      return { success: false as const, error: sessionResult.stderr || "Session not found" };
    }

    let session: Record<string, unknown>;
    try {
      session = JSON.parse(sessionResult.stdout);
    } catch {
      return { success: false as const, error: "Failed to parse session data" };
    }

    // Fetch associated events for the session
    const snapshotHash = session.snapshot_hash as string | undefined;
    const eventsResult = await sb.exec(
      `pixl events ${sessionId} --json --limit 1000`,
      { timeout: commandTimeout },
    );

    const parseArray = (stdout: string): unknown[] => {
      try {
        const parsed = JSON.parse(stdout);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    };

    // Extract node_instances from session data for a self-contained bundle
    const nodeInstances = session.node_instances ?? {};
    const nodeList = Object.entries(nodeInstances as Record<string, unknown>).map(
      ([nodeId, data]) => ({ node_id: nodeId, ...(data as Record<string, unknown>) }),
    );

    return {
      success: true as const,
      bundle: {
        session,
        node_instances: nodeList,
        events: parseArray(eventsResult.stdout),
        snapshot: snapshotHash ?? null,
        exported_at: new Date().toISOString(),
        sandbox_id: sandboxId,
      },
    };
  });

  await logOperation(sb, {
    timestamp: new Date().toISOString(),
    operation: "session_export",
    duration_ms,
    success: result.success,
    meta: { sessionId },
  });

  if (!result.success) {
    return c.json({ success: false, error: result.error }, 404);
  }

  return c.json(result.bundle);
});

// Import a session bundle into this sandbox (for cross-sandbox migration)
app.post("/sandboxes/:id/sessions/import", async (c) => {
  if (!requireScope(c, "write")) {
    return c.json({ error: "Insufficient scope" }, 403);
  }
  const sandboxId = c.req.param("id");
  const sb = getSandbox(c.env.Sandbox, sandboxId);
  const body = await c.req.json<SessionImportRequest>();

  if (!body.session || !body.session.id) {
    return c.json({ error: "session with id is required in bundle" }, 400);
  }

  const { result, duration_ms } = await timed(async () => {
    // Write the bundle to a temp file inside the sandbox
    const bundlePath = `/tmp/session-import-${Date.now()}.json`;
    const bundleJson = JSON.stringify(body);

    await sb.writeFile(bundlePath, bundleJson);

    // Use a Python script to import directly into the sandbox's pixl.db
    // This avoids requiring a dedicated `pixl session import` CLI command
    const importScript = `
import json, sqlite3, sys
with open('${bundlePath}') as f:
    bundle = json.load(f)
s = bundle['session']
sid = s['id']
db = sqlite3.connect('/workspace/.pixl/pixl.db')
db.execute('PRAGMA journal_mode=WAL')
db.execute(
    """INSERT OR REPLACE INTO workflow_sessions
       (id, feature_id, snapshot_hash, status, created_at,
        started_at, ended_at, last_updated_at, baseline_commit,
        workspace_root, sandbox_origin_id)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (sid, s.get('feature_id'), s.get('snapshot_hash', 'imported'),
     s.get('status', 'completed'), s.get('created_at'),
     s.get('started_at'), s.get('ended_at'), s.get('last_updated_at'),
     s.get('baseline_commit'), s.get('workspace_root'),
     s.get('sandbox_origin_id', bundle.get('sandbox_id'))))
for ni in bundle.get('node_instances', []):
    db.execute(
        """INSERT OR REPLACE INTO node_instances
           (session_id, node_id, state, attempt, ready_at,
            started_at, ended_at, blocked_reason, output_json,
            failure_kind, error_message, model_name, agent_name,
            input_tokens, output_tokens, total_tokens, cost_usd)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sid, ni.get('node_id'), ni.get('state', 'task_pending'),
         ni.get('attempt', 0), ni.get('ready_at'), ni.get('started_at'),
         ni.get('ended_at'), ni.get('blocked_reason'),
         json.dumps(ni.get('output')) if ni.get('output') else None,
         ni.get('failure_kind'), ni.get('error_message'),
         ni.get('model_name'), ni.get('agent_name'),
         ni.get('input_tokens', 0), ni.get('output_tokens', 0),
         ni.get('total_tokens', 0), ni.get('cost_usd', 0.0)))
for ev in bundle.get('events', []):
    try:
        db.execute(
            """INSERT OR IGNORE INTO events
               (session_id, event_type, node_id, entity_type,
                entity_id, payload, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ev.get('session_id', sid), ev.get('event_type', 'unknown'),
             ev.get('node_id'), ev.get('entity_type'),
             ev.get('entity_id'),
             json.dumps(ev.get('payload')) if ev.get('payload') else None,
             ev.get('created_at')))
    except Exception:
        pass
db.commit()
db.close()
print(json.dumps({"imported": sid}))
`;

    const importResult = await sb.exec(
      `python3 -c ${shellEscape(importScript)}`,
      { timeout: 30_000 },
    );

    // Cleanup temp file
    await sb.exec(`rm -f ${bundlePath}`, { timeout: 5_000 });

    if (importResult.exitCode !== 0) {
      return {
        success: false,
        error: importResult.stderr || "Import script failed",
      };
    }

    try {
      const output = JSON.parse(importResult.stdout);
      return { success: true, imported_session_id: output.imported };
    } catch {
      return { success: true, imported_session_id: body.session.id };
    }
  });

  await logOperation(sb, {
    timestamp: new Date().toISOString(),
    operation: "session_import",
    duration_ms,
    success: result.success,
    meta: { sessionId: String(body.session.id) },
  });

  if (!result.success) {
    return c.json({ success: false, error: result.error }, 500);
  }

  return c.json({
    success: true,
    imported_session_id: result.imported_session_id,
    sandbox_id: sandboxId,
  });
});

// --- File I/O ---

// Write a file into the sandbox
app.post("/sandboxes/:id/files", async (c) => {
  const body = await c.req.json<FileWriteRequest>();
  if (!body.path || body.content === undefined) {
    return c.json({ error: "path and content are required" }, 400);
  }

  if (!validatePath(body.path)) {
    return c.json(
      {
        error:
          "invalid path — must start with /workspace and contain no '..' segments",
      },
      400,
    );
  }

  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  await sb.writeFile(body.path, body.content);

  return c.json({ success: true, path: body.path });
});

// Read a file from the sandbox
app.get("/sandboxes/:id/files/*", async (c) => {
  const filePath =
    "/" + (c.req.param("*") ?? c.req.path.split("/files/").pop() ?? "");

  if (!validatePath(filePath)) {
    return c.json(
      {
        error:
          "invalid path — must start with /workspace and contain no '..' segments",
      },
      400,
    );
  }

  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const file = await sb.readFile(filePath);

  return c.json({
    success: true,
    path: filePath,
    content: file.content,
    encoding: file.encoding,
  });
});

// --- Git ---

// Get git status, log, branch, remote
app.get("/sandboxes/:id/git", async (c) => {
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const gitInfo = await getGitInfo(sb);

  const [statusResult, logResult] = await Promise.all([
    sb.exec("git -C /workspace status --porcelain"),
    sb.exec("git -C /workspace log --oneline -20 2>/dev/null || echo ''"),
  ]);

  return c.json({
    ...gitInfo,
    status: statusResult.stdout.trim(),
    log: logResult.stdout
      .trim()
      .split("\n")
      .filter(Boolean),
  });
});

// Push to remote
app.post("/sandboxes/:id/git/push", async (c) => {
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const gitInfo = await getGitInfo(sb);

  const { result, duration_ms } = await timed(async () => {
    return sb.exec(
      `git -C /workspace push -u origin ${gitInfo.branch}`,
    );
  });

  await logOperation(sb, {
    timestamp: new Date().toISOString(),
    operation: "git_push",
    duration_ms,
    success: result.exitCode === 0,
    error: result.exitCode !== 0 ? result.stderr : undefined,
  });

  return c.json({
    success: result.exitCode === 0,
    stdout: result.stdout,
    stderr: result.stderr,
  });
});

// Configure git user/remote
app.post("/sandboxes/:id/git/config", async (c) => {
  const body = await c.req.json<GitConfigRequest>();
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const commands: string[] = [];

  if (body.userName) {
    commands.push(
      `git -C /workspace config user.name ${shellEscape(body.userName)}`,
    );
  }
  if (body.userEmail) {
    commands.push(
      `git -C /workspace config user.email ${shellEscape(body.userEmail)}`,
    );
  }
  if (body.remoteUrl) {
    commands.push(
      `git -C /workspace remote set-url origin ${shellEscape(body.remoteUrl)} 2>/dev/null || git -C /workspace remote add origin ${shellEscape(body.remoteUrl)}`,
    );
  }

  if (commands.length === 0) {
    return c.json({ error: "at least one config field required" }, 400);
  }

  const result = await sb.exec(commands.join(" && "));

  return c.json({
    success: result.exitCode === 0,
    stderr: result.stderr || undefined,
  });
});

// --- Background processes ---

// Start a background process
app.post("/sandboxes/:id/process/start", async (c) => {
  const body = await c.req.json<ProcessStartRequest>();
  if (!body.command) {
    return c.json({ error: "command is required" }, 400);
  }

  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  const proc = await sb.startProcess(body.command, {
    cwd: body.cwd,
    env: body.env,
  });

  return c.json({ success: true, processId: proc.id });
});

// Kill a background process
app.delete("/sandboxes/:id/process/:pid", async (c) => {
  const sb = getSandbox(c.env.Sandbox, c.req.param("id"));
  await sb.killProcess(c.req.param("pid"));
  return c.json({ success: true });
});

export { app };
export default app;

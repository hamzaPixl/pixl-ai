import type { getSandbox } from "@cloudflare/sandbox";

type SandboxInstance = ReturnType<typeof getSandbox>;

export function extractVersion(output: string, tool: string): string {
  const match = output.match(new RegExp(`${tool}[\\s/v]+([\\d.]+)`));
  return match?.[1] ?? "unknown";
}

const SECRET_KEYS = Object.freeze([
  "ANTHROPIC_API_KEY",
  "OPENAI_API_KEY",
  "GITHUB_TOKEN",
]);

export interface SplitEnvVars {
  readonly vars: Record<string, string>;
  readonly secrets: Record<string, string>;
}

/**
 * Build env vars for a sandbox, separating secrets from regular vars.
 * Secrets are injected via a dedicated setEnvVars call so they never
 * appear in process spawn arguments or command logs.
 */
export function buildEnvVars(
  anthropicKey: string,
  openaiKey?: string,
  extra?: Record<string, string>,
): SplitEnvVars {
  const vars: Record<string, string> = {};
  const secrets: Record<string, string> = {
    ANTHROPIC_API_KEY: anthropicKey,
  };

  if (openaiKey) {
    secrets.OPENAI_API_KEY = openaiKey;
  }

  if (extra) {
    for (const [key, value] of Object.entries(extra)) {
      if (SECRET_KEYS.includes(key)) {
        secrets[key] = value;
      } else {
        vars[key] = value;
      }
    }
  }

  return { vars, secrets };
}

/** Escape a string for safe inclusion in a single-quoted shell argument. */
export function shellEscape(s: string): string {
  return "'" + s.replace(/'/g, "'\\''") + "'";
}

export function validatePath(path: string): boolean {
  if (!path.startsWith("/workspace")) return false;
  if (path.includes("..")) return false;
  if (!/^[\w./-]+$/.test(path)) return false;
  return true;
}

export async function getVersions(
  sb: SandboxInstance,
): Promise<{ pixl: string; claude: string; node: string; python: string }> {
  const [pixlResult, claudeResult, nodeResult, pythonResult] =
    await Promise.all([
      sb.exec("pixl --version"),
      sb.exec("claude --version"),
      sb.exec("node --version"),
      sb.exec("python3 --version"),
    ]);

  return {
    pixl: extractVersion(pixlResult.stdout || pixlResult.stderr, "pixl"),
    claude: extractVersion(
      claudeResult.stdout || claudeResult.stderr,
      "claude",
    ),
    node: extractVersion(nodeResult.stdout || nodeResult.stderr, "node"),
    python: extractVersion(
      pythonResult.stdout || pythonResult.stderr,
      "Python",
    ),
  };
}

export async function getGitInfo(
  sb: SandboxInstance,
): Promise<{
  branch: string;
  commit: string;
  dirty: boolean;
  remoteUrl: string | null;
}> {
  const [branchResult, commitResult, statusResult, remoteResult] =
    await Promise.all([
      sb.exec("git -C /workspace branch --show-current 2>/dev/null || echo ''"),
      sb.exec(
        "git -C /workspace rev-parse --short HEAD 2>/dev/null || echo ''",
      ),
      sb.exec("git -C /workspace status --porcelain 2>/dev/null || echo ''"),
      sb.exec(
        "git -C /workspace remote get-url origin 2>/dev/null || echo ''",
      ),
    ]);

  return {
    branch: branchResult.stdout.trim() || "main",
    commit: commitResult.stdout.trim() || "",
    dirty: statusResult.stdout.trim().length > 0,
    remoteUrl: remoteResult.stdout.trim() || null,
  };
}

export async function getProjectInfo(
  sb: SandboxInstance,
): Promise<{ initialized: boolean; sessions: number; workflows: number }> {
  const configResult = await sb.exec(
    "test -f /workspace/.pixl/config.json && echo yes || echo no",
  );
  const initialized = configResult.stdout.trim() === "yes";

  if (!initialized) {
    return { initialized, sessions: 0, workflows: 0 };
  }

  const [sessionsResult, workflowsResult] = await Promise.all([
    sb.exec(
      "pixl session list --json 2>/dev/null | python3 -c \"import sys,json; print(len(json.load(sys.stdin)))\" 2>/dev/null || echo 0",
    ),
    sb.exec("ls /workspace/.pixl/workflows/*.yaml 2>/dev/null | wc -l"),
  ]);

  return {
    initialized,
    sessions: parseInt(sessionsResult.stdout.trim()) || 0,
    workflows: parseInt(workflowsResult.stdout.trim()) || 0,
  };
}

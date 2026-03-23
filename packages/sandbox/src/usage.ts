import type { Sandbox } from "@cloudflare/sandbox";

const OPS_LOG = "/workspace/.pixl/sandbox-ops.jsonl";

export interface OperationEntry {
  timestamp: string;
  operation: string;
  duration_ms: number;
  success: boolean;
  error?: string;
  meta?: Record<string, unknown>;
}

export interface UsageSummary {
  total_operations: number;
  successful: number;
  failed: number;
  operations: OperationEntry[];
  by_operation: Record<string, { count: number; avg_ms: number; errors: number }>;
}

/** Append an operation entry to the sandbox ops log. Best-effort — never throws. */
export async function logOperation(
  sb: ReturnType<typeof import("@cloudflare/sandbox").getSandbox>,
  entry: OperationEntry,
): Promise<void> {
  try {
    const line = JSON.stringify(entry);
    await sb.exec(`mkdir -p /workspace/.pixl && echo '${line.replace(/'/g, "'\\''")}' >> ${OPS_LOG}`, {
      timeout: 5000,
    });
  } catch {
    // Best-effort logging — don't break the request
  }
}

/** Read the ops log and compute a usage summary. */
export async function readUsage(
  sb: ReturnType<typeof import("@cloudflare/sandbox").getSandbox>,
): Promise<UsageSummary> {
  const result = await sb.exec(`cat ${OPS_LOG} 2>/dev/null || echo ""`, {
    timeout: 5000,
  });

  const lines = result.stdout.trim().split("\n").filter(Boolean);
  const operations: OperationEntry[] = [];

  for (const line of lines) {
    try {
      operations.push(JSON.parse(line));
    } catch {
      // skip malformed lines
    }
  }

  const byOp: Record<string, { count: number; total_ms: number; errors: number }> = {};
  let successful = 0;
  let failed = 0;

  for (const op of operations) {
    if (op.success) successful++;
    else failed++;

    if (!byOp[op.operation]) {
      byOp[op.operation] = { count: 0, total_ms: 0, errors: 0 };
    }
    byOp[op.operation].count++;
    byOp[op.operation].total_ms += op.duration_ms;
    if (!op.success) byOp[op.operation].errors++;
  }

  const by_operation: Record<string, { count: number; avg_ms: number; errors: number }> = {};
  for (const [key, val] of Object.entries(byOp)) {
    by_operation[key] = {
      count: val.count,
      avg_ms: Math.round(val.total_ms / val.count),
      errors: val.errors,
    };
  }

  return {
    total_operations: operations.length,
    successful,
    failed,
    operations,
    by_operation,
  };
}

/** Time an async operation and return both result and duration. */
export async function timed<T>(fn: () => Promise<T>): Promise<{ result: T; duration_ms: number }> {
  const start = Date.now();
  const result = await fn();
  return { result, duration_ms: Date.now() - start };
}

import type {
  ProjectUsageResponse,
  HeartbeatRun,
  BudgetConfig,
  CostBreakdownResponse,
} from "@/types/api";
import { get, post, put, projectPath } from "./core";

export const usage = {
  summary: (): Promise<ProjectUsageResponse> =>
    get(projectPath("/cost/summary")),
};

export const budget = {
  get: (): Promise<BudgetConfig> => get(projectPath("/budget")),

  update: (monthlyUsd: number): Promise<BudgetConfig> =>
    put(projectPath("/budget"), { monthly_usd: monthlyUsd }),

  unpause: (): Promise<{ unpaused_sessions: string[]; count: number }> =>
    post(projectPath("/budget/unpause")),

  getCosts: (sessionId?: string): Promise<CostBreakdownResponse> =>
    get(projectPath("/budget/costs"), { session_id: sessionId }),
};

export const heartbeatRuns = {
  list: (sessionId: string, limit = 50): Promise<HeartbeatRun[]> =>
    get(projectPath(`/sessions/${sessionId}/runs`), { limit }),

  getActive: (
    sessionId: string,
  ): Promise<{ active_run: HeartbeatRun | null }> =>
    get(projectPath(`/sessions/${sessionId}/runs/active`)),

  getStalled: (threshold = 60): Promise<HeartbeatRun[]> =>
    get(projectPath("/runs/stalled"), { threshold }),
};

import type {
  ProjectUsageResponse,
  HeartbeatRun,
  BudgetConfig,
  CostBreakdownResponse,
} from "@/types/api";
import { get, post, put, projectPath } from "./core";

export const usage = {
  summary: async (): Promise<ProjectUsageResponse> => {
    const res = await get<any>(projectPath("/cost/summary"));
    const mapEntry = (key: string, val: any, nameField: string) => ({
      [nameField]: key,
      ...val,
      executions: val.executions ?? val.node_count ?? 0,
    });
    const toModelArray = (dict: Record<string, any> | any[]): any[] =>
      Array.isArray(dict)
        ? dict
        : Object.entries(dict ?? {}).map(([k, v]) => mapEntry(k, v, "model"));
    const toAgentArray = (dict: Record<string, any> | any[]): any[] =>
      Array.isArray(dict)
        ? dict
        : Object.entries(dict ?? {}).map(([k, v]) => mapEntry(k, v, "agent"));
    const toFeatureArray = (dict: Record<string, any> | any[]): any[] =>
      Array.isArray(dict)
        ? dict
        : Object.entries(dict ?? {}).map(([k, v]) => ({
            feature_id: k,
            feature_title: k,
            ...v,
          }));
    return {
      totals: res.totals ?? {
        cost_usd: 0,
        input_tokens: 0,
        output_tokens: 0,
        total_tokens: 0,
      },
      by_model: toModelArray(res.by_model),
      by_agent: toAgentArray(res.by_agent),
      by_feature: toFeatureArray(res.by_feature),
    };
  },
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

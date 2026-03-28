import type {
  AutonomyResponse,
  RerunResponse,
  RollbackResponse,
  EpicWavesResponse,
  EpicExecutionProgressResponse,
  EpicRunRequest,
  EpicRunResponse,
  EpicCancelResponse,
  ChainSignalListResponse,
  QualityLatestResponse,
  QualityScoresResponse,
  ChainControlResponse,
  ChainStartResponse,
  ExecutionChainSummary,
  NodeInstance,
  GateApproveRequest,
  GateRejectRequest,
  RecoveryTimeline,
  RecoveryInboxResponse,
  IncidentRecord,
  RecoveryLabData,
} from "@/types/api";
import { get, post, put, projectPath } from "./core";

export const control = {
  setAutonomy: (
    featureId: string,
    mode: "assist" | "autopilot",
  ): Promise<AutonomyResponse> =>
    put(projectPath(`/features/${featureId}/autonomy`), { mode }),

  rerun: (sessionId: string, nodeId: string): Promise<RerunResponse> =>
    post(
      projectPath(`/sessions/${sessionId}/rerun-from/${nodeId}`),
      {},
    ),

  rerunNode: (sessionId: string, nodeId: string): Promise<RerunResponse> =>
    post(
      projectPath(`/sessions/${sessionId}/nodes/${nodeId}/rerun`),
      {},
    ),

  rollback: (sessionId: string, nodeId: string): Promise<RollbackResponse> =>
    post(projectPath(`/sessions/${sessionId}/rollback`), {
      node_id: nodeId,
    }),

  pause: (
    sessionId: string,
    reason?: string,
  ): Promise<{ status: string; session_id: string }> =>
    post(projectPath(`/sessions/${sessionId}/pause`), { reason }),

  resume: (
    sessionId: string,
  ): Promise<{ status: string; session_id: string }> =>
    post(projectPath(`/sessions/${sessionId}/resume`), {}),

  forceResume: (
    sessionId: string,
  ): Promise<{ status: string; session_id: string }> =>
    post(projectPath(`/sessions/${sessionId}/resume?force=true`), {}),

  getEpicWaves: (epicId: string): Promise<EpicWavesResponse> =>
    get(projectPath(`/epics/${epicId}/waves`)),

  getEpicExecution: (epicId: string): Promise<EpicExecutionProgressResponse> =>
    get(projectPath(`/epics/${epicId}/execution`)),

  runEpic: (epicId: string, data?: EpicRunRequest): Promise<EpicRunResponse> =>
    post(projectPath(`/epics/${epicId}/run`), data || {}),

  cancelEpicExecution: (epicId: string): Promise<EpicCancelResponse> =>
    post(projectPath(`/epics/${epicId}/cancel`), {}),

  getChainSignals: (
    chainId: string,
    params?: { signal_type?: string; limit?: number },
  ): Promise<ChainSignalListResponse> =>
    get(projectPath(`/chains/${chainId}/signals`), params),

  getChainQuality: (chainId: string): Promise<QualityLatestResponse> =>
    get(projectPath(`/chains/${chainId}/quality`)),

  getQualityTrends: (params: {
    scope_type: string;
    scope_id: string;
    metric: string;
    limit?: number;
  }): Promise<QualityScoresResponse> =>
    get(projectPath("/quality/trends"), params),

  startChain: (chainId: string): Promise<ChainStartResponse> =>
    post(projectPath(`/chains/${chainId}/start`), {}),

  pauseChain: (chainId: string): Promise<ChainControlResponse> =>
    post(projectPath(`/chains/${chainId}/pause`), {}),

  resumeChain: (chainId: string): Promise<ChainControlResponse> =>
    post(projectPath(`/chains/${chainId}/resume`), {}),

  cancelChain: (chainId: string): Promise<ChainControlResponse> =>
    post(projectPath(`/chains/${chainId}/cancel`), {}),

  resetChain: (chainId: string): Promise<ChainControlResponse> =>
    post(projectPath(`/chains/${chainId}/reset`), {}),
};

export const chains = {
  list: async (): Promise<ExecutionChainSummary[]> => {
    const res = await get<
      { chains: ExecutionChainSummary[] } | ExecutionChainSummary[]
    >(projectPath("/chains"));
    return Array.isArray(res) ? res : (res.chains ?? []);
  },

  get: (id: string): Promise<ExecutionChainSummary> =>
    get(projectPath(`/chains/${id}`)),
};

export const gates = {
  list: (sessionId: string): Promise<NodeInstance[]> =>
    get(projectPath(`/gates/${sessionId}`)),

  approve: (
    sessionId: string,
    gateId: string,
    data?: GateApproveRequest,
  ): Promise<{ status: string; gate_id: string }> =>
    post(projectPath(`/gates/${sessionId}/${gateId}/approve`), data),

  reject: (
    sessionId: string,
    gateId: string,
    data?: GateRejectRequest,
  ): Promise<{ status: string; gate_id: string }> =>
    post(projectPath(`/gates/${sessionId}/${gateId}/reject`), data),
};

export const recovery = {
  explain: (sessionId: string): Promise<RecoveryTimeline> =>
    get(projectPath(`/recovery/${sessionId}/explain`)),

  retry: (
    sessionId: string,
    nodeId: string,
    data?: { note?: string },
  ): Promise<{ status: string; node_id: string }> =>
    post(projectPath(`/recovery/${sessionId}/${nodeId}/retry`), data),

  skip: (
    sessionId: string,
    nodeId: string,
    data?: { reason?: string },
  ): Promise<{ status: string; node_id: string }> =>
    post(projectPath(`/recovery/${sessionId}/${nodeId}/skip`), data),

  inbox: (): Promise<RecoveryInboxResponse> =>
    get(projectPath("/recovery/inbox")),

  incidents: (params?: {
    limit?: number;
    offset?: number;
  }): Promise<IncidentRecord[]> =>
    get(projectPath("/recovery/incidents"), params),

  lab: (): Promise<RecoveryLabData> => get(projectPath("/views/recovery-lab")),
};

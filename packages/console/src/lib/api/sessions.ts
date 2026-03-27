import type {
  WorkflowSession,
  SessionReportJob,
  SessionListEntry,
  NodeInstance,
  Event,
  TransitionRecord,
  ListParams,
} from "@/types/api";
import { get, post, projectPath, unwrapItems } from "./core";

/** Normalise backend event fields to frontend Event shape. */
function normalizeEvent(e: any): Event {
  return {
    ...e,
    type: e.event_type ?? e.type,
    timestamp: e.created_at ?? e.timestamp,
    data: e.payload ?? e.data ?? {},
  };
}

export const sessions = {
  list: (params?: ListParams): Promise<SessionListEntry[]> =>
    get(projectPath("/sessions"), params),

  active: (): Promise<SessionListEntry[]> =>
    get(projectPath("/sessions/active")),

  get: (id: string): Promise<WorkflowSession> =>
    get(projectPath(`/sessions/${id}`)),

  nodes: (id: string): Promise<NodeInstance[]> =>
    get(projectPath(`/sessions/${id}/nodes`)),

  node: (sessionId: string, nodeId: string): Promise<NodeInstance> =>
    get(projectPath(`/sessions/${sessionId}/nodes/${nodeId}`)),

  pause: (
    id: string,
    reason?: string,
  ): Promise<{ status: string; session_id: string }> =>
    post(projectPath(`/control/sessions/${id}/pause`), { reason }),

  resume: (id: string): Promise<{ status: string; session_id: string }> =>
    post(projectPath(`/control/sessions/${id}/resume`), {}),

  draftReport: (id: string, requestedBy = "ui"): Promise<SessionReportJob> =>
    post(projectPath(`/sessions/${id}/report-draft`), {
      requested_by: requestedBy,
    }),

  reportJobs: (
    id: string,
    params?: { limit?: number },
  ): Promise<SessionReportJob[]> =>
    get(projectPath(`/sessions/${id}/report-jobs`), params),
};

export const events = {
  list: async (params?: {
    limit?: number;
    offset?: number;
    session_id?: string;
  }): Promise<Event[]> => {
    const res = await get<{ items: any[] } | any[]>(
      projectPath("/events"),
      params,
    );
    return unwrapItems(res).map(normalizeEvent);
  },

  recent: async (limit = 50): Promise<Event[]> => {
    const res = await get<{ items: any[] } | any[]>(
      projectPath("/events/recent"),
      { limit },
    );
    return unwrapItems(res).map(normalizeEvent);
  },

  history: (entityId: string): Promise<TransitionRecord[]> =>
    get(projectPath(`/events/history/${entityId}`)),

  counts: (params?: { session_id?: string }): Promise<Record<string, number>> =>
    get(projectPath("/events/counts"), params),

  transitions: (sessionId?: string): Promise<TransitionRecord[]> =>
    get(projectPath("/events/transitions"), { session_id: sessionId }),
};

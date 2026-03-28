/**
 * Query key factory for React Query.
 *
 * All keys are prefixed with projectId to ensure proper cache isolation
 * between projects. When the project changes, all queries are invalidated.
 */

export const queryKeys = {
  // Sessions
  sessions: {
    all: (projectId: string) => [projectId, "sessions"] as const,
    list: (projectId: string, params?: Record<string, unknown>) =>
      [projectId, "sessions", "list", params] as const,
    active: (projectId: string) => [projectId, "sessions", "active"] as const,
    detail: (projectId: string, id: string) =>
      [projectId, "sessions", "detail", id] as const,
    nodes: (projectId: string, id: string) =>
      [projectId, "sessions", "nodes", id] as const,
    node: (projectId: string, sessionId: string, nodeId: string) =>
      [projectId, "sessions", "node", sessionId, nodeId] as const,
    reportJobs: (projectId: string, sessionId: string, limit?: number) =>
      [projectId, "sessions", "report-jobs", sessionId, limit] as const,
  },

  // Events
  events: {
    all: (projectId: string) => [projectId, "events"] as const,
    list: (projectId: string, params?: Record<string, unknown>) =>
      [projectId, "events", "list", params] as const,
    recent: (projectId: string, limit?: number) =>
      [projectId, "events", "recent", limit] as const,
    history: (projectId: string, entityId: string) =>
      [projectId, "events", "history", entityId] as const,
    counts: (projectId: string, params?: Record<string, unknown>) =>
      [projectId, "events", "counts", params] as const,
    transitions: (projectId: string, sessionId?: string) =>
      [projectId, "events", "transitions", sessionId] as const,
  },

  // Gates
  gates: {
    all: (projectId: string) => [projectId, "gates"] as const,
    list: (projectId: string, sessionId: string) =>
      [projectId, "gates", "list", sessionId] as const,
    inbox: (projectId: string) => [projectId, "gates", "inbox"] as const,
  },

  // Features
  features: {
    all: (projectId: string) => [projectId, "features"] as const,
    list: (projectId: string, params?: Record<string, unknown>) =>
      [projectId, "features", "list", params] as const,
    detail: (projectId: string, id: string) =>
      [projectId, "features", "detail", id] as const,
    history: (projectId: string, id: string) =>
      [projectId, "features", "history", id] as const,
    transitions: (projectId: string, id: string) =>
      [projectId, "features", "transitions", id] as const,
    activeSession: (projectId: string, id: string) =>
      [projectId, "features", "active-session", id] as const,
  },

  // Epics
  epics: {
    all: (projectId: string) => [projectId, "epics"] as const,
    list: (projectId: string, params?: Record<string, unknown>) =>
      [projectId, "epics", "list", params] as const,
    detail: (projectId: string, id: string) =>
      [projectId, "epics", "detail", id] as const,
    history: (projectId: string, id: string) =>
      [projectId, "epics", "history", id] as const,
    transitions: (projectId: string, id: string) =>
      [projectId, "epics", "transitions", id] as const,
    features: (projectId: string, id: string) =>
      [projectId, "epics", "features", id] as const,
  },

  // Artifacts
  artifacts: {
    all: (projectId: string) => [projectId, "artifacts"] as const,
    list: (projectId: string, params?: Record<string, unknown>) =>
      [projectId, "artifacts", "list", params] as const,
    detail: (projectId: string, id: string) =>
      [projectId, "artifacts", "detail", id] as const,
    content: (projectId: string, id: string) =>
      [projectId, "artifacts", "content", id] as const,
    search: (projectId: string, query: string, params?: Record<string, unknown>) =>
      [projectId, "artifacts", "search", query, params] as const,
  },

  // Knowledge
  knowledge: {
    all: (projectId: string) => [projectId, "knowledge"] as const,
    search: (projectId: string, query: string, params?: Record<string, unknown>) =>
      [projectId, "knowledge", "search", query, params] as const,
    status: (projectId: string) => [projectId, "knowledge", "status"] as const,
  },

  // Workflows
  workflows: {
    list: (projectId: string) => [projectId, "workflows", "list"] as const,
    detail: (projectId: string, workflowId: string) =>
      [projectId, "workflows", "detail", workflowId] as const,
  },

  // Agents
  agents: {
    all: (projectId: string) => [projectId, "agents"] as const,
    list: (projectId: string) => [projectId, "agents", "list"] as const,
    models: (projectId: string) => [projectId, "agents", "models"] as const,
    classificationModel: (projectId: string) =>
      [projectId, "agents", "classification-model"] as const,
    sessionReportModel: (projectId: string) =>
      [projectId, "agents", "session-report-model"] as const,
  },

  // Root-level (not project-scoped)
  projects: {
    list: () => ["projects", "list"] as const,
    detail: (id: string) => ["projects", "detail", id] as const,
  },

  doctor: {
    check: () => ["doctor", "check"] as const,
  },

  // Dashboard
  dashboard: {
    all: (projectId: string) => [projectId, "dashboard"] as const,
    summary: (projectId: string) => [projectId, "dashboard", "summary"] as const,
    progress: (projectId: string) => [projectId, "dashboard", "progress"] as const,
    overview: (projectId: string) => [projectId, "dashboard", "overview"] as const,
  },

  // Views (pre-aggregated projections)
  views: {
    epics: (projectId: string) => [projectId, "views", "epics"] as const,
    epic: (projectId: string, epicId: string) => [projectId, "views", "epic", epicId] as const,
    epicFeatures: (projectId: string, epicId: string) => [projectId, "views", "epic-features", epicId] as const,
    roadmaps: (projectId: string) => [projectId, "views", "roadmaps"] as const,
    gateInbox: (projectId: string) => [projectId, "views", "gate-inbox"] as const,
  },

  // Recovery
  recovery: {
    all: (projectId: string) => [projectId, "recovery"] as const,
    inbox: (projectId: string) => [projectId, "recovery", "inbox"] as const,
    incidents: (projectId: string, params?: Record<string, unknown>) =>
      [projectId, "recovery", "incidents", params] as const,
    lab: (projectId: string) => [projectId, "recovery", "lab"] as const,
    explain: (projectId: string, sessionId: string) =>
      [projectId, "recovery", "explain", sessionId] as const,
  },

  // Usage
  usage: {
    all: (projectId: string) => [projectId, "usage"] as const,
    summary: (projectId: string) => [projectId, "usage", "summary"] as const,
  },

  // Chains
  chains: {
    all: (projectId: string) => [projectId, "chains"] as const,
    list: (projectId: string) => [projectId, "chains", "list"] as const,
    detail: (projectId: string, id: string) =>
      [projectId, "chains", "detail", id] as const,
    signals: (projectId: string, id: string) =>
      [projectId, "chains", "signals", id] as const,
    quality: (projectId: string, id: string) =>
      [projectId, "chains", "quality", id] as const,
  },

  // Heartbeat Runs
  heartbeatRuns: {
    all: (projectId: string) => [projectId, "heartbeat-runs"] as const,
    list: (projectId: string, sessionId: string) =>
      [projectId, "heartbeat-runs", "list", sessionId] as const,
    active: (projectId: string, sessionId: string) =>
      [projectId, "heartbeat-runs", "active", sessionId] as const,
    stalled: (projectId: string) =>
      [projectId, "heartbeat-runs", "stalled"] as const,
  },

  // Budget
  budget: {
    all: (projectId: string) => [projectId, "budget"] as const,
    config: (projectId: string) => [projectId, "budget", "config"] as const,
    costs: (projectId: string, sessionId?: string) =>
      [projectId, "budget", "costs", sessionId] as const,
  },

  // Metrics
  metrics: {
    agents: (projectId: string, timeframe?: number) =>
      [projectId, "metrics", "agents", timeframe] as const,
    agent: (projectId: string, name: string, timeframe?: number) =>
      [projectId, "metrics", "agent", name, timeframe] as const,
  },

  // Roadmaps
  roadmaps: {
    all: (projectId: string) => [projectId, "roadmaps"] as const,
    list: (projectId: string, params?: { limit?: number; offset?: number; status?: string }) =>
      [projectId, "roadmaps", "list", params] as const,
    detail: (projectId: string, id: string) =>
      [projectId, "roadmaps", "detail", id] as const,
    epics: (projectId: string, id: string) =>
      [projectId, "roadmaps", "epics", id] as const,
    milestones: (projectId: string, id: string) =>
      [projectId, "roadmaps", "milestones", id] as const,
    history: (projectId: string, id: string) =>
      [projectId, "roadmaps", "history", id] as const,
    transitions: (projectId: string, id: string) =>
      [projectId, "roadmaps", "transitions", id] as const,
  },
};

/**
 * Invalidate all queries for a specific project.
 * Call this when switching projects.
 */
export function projectQueryPrefix(projectId: string) {
  return [projectId];
}

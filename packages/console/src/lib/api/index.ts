/**
 * Barrel re-export for the API client.
 *
 * All existing imports from '@/lib/api' continue to work unchanged.
 */

// Core helpers
export {
  ApiRequestError,
  get,
  post,
  put,
  patch,
  del,
  delWithBody,
  setApiProjectContext,
  getApiProjectContext,
  setApiWorkspaceContext,
  getWsUrl,
  projectPath,
} from "./core";

// Domain modules
export { sessions, events } from "./sessions";
export { features, epics, roadmaps } from "./work-items";
export { control, chains, gates, recovery } from "./control";
export { agents } from "./agents";
export { dashboard, views } from "./dashboard";
export { auth, workspacesApi } from "./auth";
export { run, workflows } from "./run";
export { usage, budget, heartbeatRuns } from "./usage";
export { artifacts } from "./artifacts";
export { projects, projectSettings } from "./projects";
export { github } from "./github";
export { sandboxes } from "./sandboxes";
export type { SandboxInfo, ExecResult, WorkflowRunResult } from "./sandboxes";

// Combined api object (preserves `import { api } from '@/lib/api'`)
import { get, post, put, patch, del, delWithBody } from "./core";
import { sessions, events } from "./sessions";
import { features, epics, roadmaps } from "./work-items";
import { control, chains, gates, recovery } from "./control";
import { agents } from "./agents";
import { dashboard, views } from "./dashboard";
import { auth, workspacesApi } from "./auth";
import { run, workflows } from "./run";
import { usage, budget, heartbeatRuns } from "./usage";
import { artifacts } from "./artifacts";
import { projects, projectSettings } from "./projects";
import { github } from "./github";
import { sandboxes } from "./sandboxes";

export const api = {
  get,
  post,
  put,
  patch,
  del,
  delWithBody,

  auth,
  workspacesApi,
  sessions,
  events,
  gates,
  artifacts,
  projects,
  recovery,
  run,
  workflows,
  agents,
  dashboard,
  roadmaps,
  views,
  features,
  epics,
  control,
  usage,
  chains,
  heartbeatRuns,
  budget,
  projectSettings,
  github,
  sandboxes,
};

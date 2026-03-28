import type {
  RunRequest,
  ClassificationResponse,
  ConfirmRunRequest,
  RunFeatureRequest,
  RunStartResponse,
  WorkflowSummary,
  WorkflowDetail,
} from "@/types/api";
import { get, post, projectPath } from "./core";

export const run = {
  classify: (data: RunRequest): Promise<ClassificationResponse> =>
    post(projectPath("/run"), data),

  confirm: (data: ConfirmRunRequest): Promise<RunStartResponse> =>
    post(projectPath("/run/confirm"), data),

  runFeature: (
    featureId: string,
    data: RunFeatureRequest,
  ): Promise<RunStartResponse> =>
    post(projectPath(`/run/feature/${featureId}`), data),
};

export const workflows = {
  list: (): Promise<WorkflowSummary[]> => get(projectPath("/workflows")),

  detail: (workflowId: string): Promise<WorkflowDetail> =>
    get(projectPath(`/workflows/${workflowId}`)),
};

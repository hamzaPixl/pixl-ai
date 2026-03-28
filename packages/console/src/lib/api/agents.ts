import type {
  AgentInfo,
  ClassificationModelInfo,
  SessionReportModelInfo,
  UpdateAgentModelRequest,
  UpdateClassificationModelRequest,
  UpdateSessionReportModelRequest,
} from "@/types/api";
import { get, put, projectPath } from "./core";

export const agents = {
  list: (): Promise<AgentInfo[]> => get(projectPath("/agents")),

  allowedModels: (): Promise<string[]> => get(projectPath("/agents/models")),

  classificationModel: (): Promise<ClassificationModelInfo> =>
    get(projectPath("/agents/classification-model")),

  updateClassificationModel: (
    data: UpdateClassificationModelRequest,
  ): Promise<ClassificationModelInfo> =>
    put(projectPath("/agents/classification-model"), data),

  sessionReportModel: (): Promise<SessionReportModelInfo> =>
    get(projectPath("/agents/session-report-model")),

  updateSessionReportModel: (
    data: UpdateSessionReportModelRequest,
  ): Promise<SessionReportModelInfo> =>
    put(projectPath("/agents/session-report-model"), data),

  updateModel: (
    agentName: string,
    data: UpdateAgentModelRequest,
  ): Promise<AgentInfo> => put(projectPath(`/agents/${agentName}/model`), data),
};

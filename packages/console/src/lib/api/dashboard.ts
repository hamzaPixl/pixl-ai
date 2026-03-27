import type {
  DashboardSummary,
  ProgressResponse,
  DashboardOverview,
  EpicRollup,
  RoadmapRollup,
  GateInboxResponse,
  ActiveSessionData,
  FeatureDetail,
  RecoveryLabData,
  WorkItem,
} from "@/types/api";
import { get, projectPath } from "./core";

export const dashboard = {
  summary: (): Promise<DashboardSummary> =>
    get(projectPath("/dashboard/summary")),

  progress: (): Promise<ProgressResponse> =>
    get(projectPath("/dashboard/progress")),

  overview: (): Promise<DashboardOverview> =>
    get(projectPath("/dashboard/overview")),
};

export const views = {
  epics: (): Promise<EpicRollup[]> => get(projectPath("/views/epics")),

  epic: (epicId: string): Promise<EpicRollup> =>
    get(projectPath(`/views/epics/${epicId}`)),

  epicFeatures: (epicId: string): Promise<WorkItem[]> =>
    get(projectPath(`/views/epics/${epicId}/features`)),

  roadmaps: (): Promise<RoadmapRollup[]> => get(projectPath("/views/roadmaps")),

  gateInbox: (): Promise<GateInboxResponse> =>
    get(projectPath("/views/gate-inbox")),

  featureActiveSession: (featureId: string): Promise<ActiveSessionData> =>
    get(projectPath(`/views/features/${featureId}/active-session`)),

  featureDetail: (featureId: string): Promise<FeatureDetail> =>
    get(projectPath(`/views/features/${featureId}`)),

  recoveryLab: (): Promise<RecoveryLabData> =>
    get(projectPath("/views/recovery-lab")),
};

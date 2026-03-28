import type {
  WorkItem,
  Feature,
  TransitionRequest,
  TransitionResponse,
  TransitionRecord,
  CreateRoadmapRequest,
  UpdateRoadmapRequest,
  CreateMilestoneRequest,
  CreateFeatureRequest,
  UpdateFeatureRequest,
  CreateEpicRequest,
  UpdateEpicRequest,
  Milestone,
} from "@/types/api";
import { get, post, patch, del, projectPath } from "./core";

export const features = {
  list: async (params?: {
    limit?: number;
    offset?: number;
    status?: string;
  }): Promise<Feature[]> => {
    const res = await get<{ items: Feature[] } | Feature[]>(
      projectPath("/features"),
      params,
    );
    return Array.isArray(res) ? res : res.items;
  },

  get: (id: string): Promise<Feature> => get(projectPath(`/features/${id}`)),

  create: (data: CreateFeatureRequest): Promise<Feature> =>
    post(projectPath("/features"), { ...data, type: "feature" }),

  update: (id: string, data: UpdateFeatureRequest): Promise<Feature> =>
    patch(projectPath(`/features/${id}`), data),

  delete: (id: string): Promise<{ deleted: boolean }> =>
    del(projectPath(`/features/${id}`)),

  transition: (
    id: string,
    data: TransitionRequest,
  ): Promise<TransitionResponse> =>
    post(projectPath(`/features/${id}/transition`), data),

  history: (id: string): Promise<TransitionRecord[]> =>
    get(projectPath(`/features/${id}/history`)),

  transitions: (id: string): Promise<TransitionRecord[]> =>
    get(projectPath(`/features/${id}/transitions`)),

  notes: {
    add: (id: string, note: string): Promise<Feature> =>
      post(projectPath(`/features/${id}/notes`), { note }),
  },
};

export const epics = {
  list: (params?: {
    limit?: number;
    offset?: number;
    status?: string;
  }): Promise<WorkItem[]> => get(projectPath("/epics"), params),

  get: (id: string): Promise<WorkItem> => get(projectPath(`/epics/${id}`)),

  create: (data: CreateEpicRequest & { type?: "epic" }): Promise<WorkItem> =>
    post(projectPath("/epics"), { ...data, type: "epic" }),

  update: (id: string, data: UpdateEpicRequest): Promise<WorkItem> =>
    patch(projectPath(`/epics/${id}`), data),

  delete: (id: string): Promise<{ deleted: boolean }> =>
    del(projectPath(`/epics/${id}`)),

  transition: (
    id: string,
    data: TransitionRequest,
  ): Promise<TransitionResponse> =>
    post(projectPath(`/epics/${id}/transition`), data),

  history: (id: string): Promise<TransitionRecord[]> =>
    get(projectPath(`/epics/${id}/history`)),

  transitions: (id: string): Promise<TransitionRecord[]> =>
    get(projectPath(`/epics/${id}/transitions`)),

  features: {
    list: (id: string): Promise<WorkItem[]> =>
      get(projectPath(`/epics/${id}/features`)),
  },
};

export const roadmaps = {
  list: (params?: {
    limit?: number;
    offset?: number;
    status?: string;
  }): Promise<WorkItem[]> => get(projectPath("/roadmaps"), params),

  get: (id: string): Promise<WorkItem> => get(projectPath(`/roadmaps/${id}`)),

  create: (
    data: CreateRoadmapRequest & { type?: "roadmap" },
  ): Promise<WorkItem> =>
    post(projectPath("/roadmaps"), { ...data, type: "roadmap" }),

  update: (id: string, data: UpdateRoadmapRequest): Promise<WorkItem> =>
    patch(projectPath(`/roadmaps/${id}`), data),

  delete: (id: string): Promise<{ deleted: boolean }> =>
    del(projectPath(`/roadmaps/${id}`)),

  transition: (
    id: string,
    data: TransitionRequest,
  ): Promise<TransitionResponse> =>
    post(projectPath(`/roadmaps/${id}/transition`), data),

  epics: (id: string): Promise<WorkItem[]> =>
    get(projectPath(`/roadmaps/${id}/epics`)),

  history: (id: string): Promise<TransitionRecord[]> =>
    get(projectPath(`/roadmaps/${id}/history`)),

  transitions: (id: string): Promise<TransitionRecord[]> =>
    get(projectPath(`/roadmaps/${id}/transitions`)),

  milestones: {
    list: (roadmapId: string): Promise<Milestone[]> =>
      get(projectPath(`/roadmaps/${roadmapId}/milestones`)),

    create: (
      roadmapId: string,
      data: CreateMilestoneRequest,
    ): Promise<Milestone> =>
      post(projectPath(`/roadmaps/${roadmapId}/milestones`), data),

    update: (
      roadmapId: string,
      milestoneId: string,
      data: Partial<Milestone>,
    ): Promise<Milestone> =>
      patch(
        projectPath(`/roadmaps/${roadmapId}/milestones/${milestoneId}`),
        data,
      ),

    delete: (
      roadmapId: string,
      milestoneId: string,
    ): Promise<{ deleted: boolean }> =>
      del(projectPath(`/roadmaps/${roadmapId}/milestones/${milestoneId}`)),
  },
};

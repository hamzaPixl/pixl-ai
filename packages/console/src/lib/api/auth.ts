import { get, post, patch, del } from "./core";

export const auth = {
  signup: (data: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
  }): Promise<{ user: unknown; token: string }> => post("/auth/signup", data),

  login: (data: {
    email: string;
    password: string;
  }): Promise<{ user: unknown; token: string }> => post("/auth/login", data),

  logout: (): Promise<{ message: string }> => post("/auth/logout"),

  me: (): Promise<{ user: unknown }> => get("/auth/me"),

  refresh: (): Promise<{ user: unknown; token: string }> =>
    post("/auth/refresh"),

  updateProfile: (data: {
    first_name?: string;
    last_name?: string;
    theme?: string;
    avatar?: string;
  }): Promise<{ user: unknown }> => patch("/auth/me", data),

  completeOnboarding: (): Promise<{ message: string }> =>
    post("/auth/me/onboarding-complete"),

  changePassword: (data: {
    current_password: string;
    new_password: string;
  }): Promise<{ message: string }> => post("/auth/me/password", data),

  deleteAccount: (data: { password: string }): Promise<{ message: string }> =>
    post("/auth/me/delete", data),
};

export interface ApiKeyOut {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  rate_limit_rpm: number;
  is_active: boolean;
  created_at: string;
}

export interface CreateApiKeyResponse {
  id: string;
  key: string;
  name: string;
  prefix: string;
  scopes: string[];
  rate_limit_rpm: number;
}

export const apiKeysApi = {
  list: (): Promise<ApiKeyOut[]> => get("/keys"),

  create: (data: {
    name: string;
    scopes?: string[];
    rate_limit_rpm?: number;
  }): Promise<CreateApiKeyResponse> => post("/keys", data),

  revoke: (keyId: string): Promise<{ message: string }> =>
    del(`/keys/${keyId}`),
};

export const workspacesApi = {
  list: (): Promise<{ workspaces: unknown[] }> => get("/workspaces"),

  create: (data: {
    name: string;
    slug?: string;
    description?: string;
  }): Promise<{ workspace: unknown }> => post("/workspaces", data),

  get: (id: string): Promise<{ workspace: unknown }> =>
    get(`/workspaces/${id}`),

  members: (id: string): Promise<{ members: unknown[] }> =>
    get(`/workspaces/${id}/members`),

  invite: (
    wsId: string,
    data: { email: string; role?: string },
  ): Promise<{ invitation: unknown }> =>
    post(`/workspaces/${wsId}/invitations`, data),

  bulkInvite: (
    wsId: string,
    data: { invitations: Array<{ email: string; role?: string }> },
  ): Promise<{ invitations: unknown[] }> =>
    post(`/workspaces/${wsId}/invitations/bulk`, data),

  teams: (id: string): Promise<{ teams: unknown[] }> =>
    get(`/workspaces/${id}/teams`),

  createTeam: (
    wsId: string,
    data: { name: string; description?: string; color?: string },
  ): Promise<{ team: unknown }> => post(`/workspaces/${wsId}/teams`, data),

  updateTeam: (
    wsId: string,
    teamId: string,
    data: { name?: string; description?: string; color?: string },
  ): Promise<{ team: unknown }> =>
    patch(`/workspaces/${wsId}/teams/${teamId}`, data),

  deleteTeam: (wsId: string, teamId: string): Promise<{ message: string }> =>
    del(`/workspaces/${wsId}/teams/${teamId}`),

  teamMembers: (
    wsId: string,
    teamId: string,
  ): Promise<{ members: unknown[] }> =>
    get(`/workspaces/${wsId}/teams/${teamId}/members`),

  addTeamMember: (
    wsId: string,
    teamId: string,
    userId: string,
  ): Promise<{ message: string }> =>
    post(`/workspaces/${wsId}/teams/${teamId}/members`, { user_id: userId }),

  removeTeamMember: (
    wsId: string,
    teamId: string,
    userId: string,
  ): Promise<{ message: string }> =>
    del(`/workspaces/${wsId}/teams/${teamId}/members/${userId}`),

  projects: (id: string): Promise<{ projects: unknown[] }> =>
    get(`/workspaces/${id}/projects`),

  linkProject: (
    wsId: string,
    projectId: string,
  ): Promise<{ message: string }> =>
    post(`/workspaces/${wsId}/projects/${projectId}/link`),

  changeRole: (
    wsId: string,
    userId: string,
    role: string,
  ): Promise<{ message: string; role: string }> =>
    patch(`/workspaces/${wsId}/members/${userId}/role`, { role }),

  invitations: (
    wsId: string,
  ): Promise<{
    invitations: Array<{
      id: string;
      email: string;
      role: string;
      status: string;
      created_at: string;
    }>;
  }> => get(`/workspaces/${wsId}/invitations`),

  revokeInvitation: (
    wsId: string,
    invId: string,
  ): Promise<{ message: string }> =>
    del(`/workspaces/${wsId}/invitations/${invId}`),

  leave: (wsId: string): Promise<{ message: string }> =>
    post(`/workspaces/${wsId}/leave`),

  delete: (wsId: string): Promise<{ message: string }> =>
    del(`/workspaces/${wsId}`),
};

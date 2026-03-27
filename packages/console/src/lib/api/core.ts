/**
 * Core HTTP helpers, project context, and error class.
 */

const API_BASE = "/api";

// Project Context

let _currentProjectId: string | null = null;
let _currentWorkspaceId: string | null = null;

export function setApiWorkspaceContext(workspaceId: string | null): void {
  _currentWorkspaceId = workspaceId;
}

export function setApiProjectContext(projectId: string | null): void {
  _currentProjectId = projectId;
}

export function getApiProjectContext(): string | null {
  return _currentProjectId;
}

export function projectPath(path: string): string {
  if (!_currentProjectId) {
    throw new Error("No project selected. Call setApiProjectContext() first.");
  }
  return `/projects/${_currentProjectId}${path}`;
}

export function getCurrentProjectId(): string | null {
  return _currentProjectId;
}

export class ApiRequestError extends Error {
  status: number;
  detail: string;
  body: Record<string, unknown>;

  constructor(status: number, detail: string, body?: Record<string, unknown>) {
    super(detail);
    this.name = "ApiRequestError";
    this.status = status;
    this.detail = detail;
    this.body = body ?? {};
  }
}

const AUTH_EXEMPT_PATHS = [
  "/auth/refresh",
  "/auth/me",
  "/auth/login",
  "/auth/signup",
];

async function handleResponse<T>(
  response: Response,
  requestPath: string,
): Promise<T> {
  if (!response.ok) {
    if (
      response.status === 401 &&
      !AUTH_EXEMPT_PATHS.some((p) => requestPath.startsWith(p))
    ) {
      const { useAuthStore } = await import("@/stores/auth");
      useAuthStore.getState().logout();
    }

    let errorDetail = "An error occurred";
    let errorBody: Record<string, unknown> = {};
    try {
      const body = await response.json();
      errorBody = body;
      errorDetail = body.error || body.detail || errorDetail;
    } catch {
      errorDetail = response.statusText || errorDetail;
    }
    throw new ApiRequestError(response.status, errorDetail, errorBody);
  }
  return response.json();
}

function fetchApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (_currentWorkspaceId) headers["X-Workspace-ID"] = _currentWorkspaceId;
  return fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options,
    headers: { ...headers, ...(options.headers as Record<string, string>) },
  }).then((res) => handleResponse<T>(res, path));
}

function urlWithParams(
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
): string {
  if (!params) return path;
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) url.searchParams.set(key, String(value));
  });
  const qs = url.searchParams.toString();
  return qs ? `${path}?${qs}` : path;
}

export function get<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
): Promise<T> {
  return fetchApi<T>(urlWithParams(path, params));
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return fetchApi<T>(path, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
}

export function put<T>(path: string, body: unknown): Promise<T> {
  return fetchApi<T>(path, { method: "PUT", body: JSON.stringify(body) });
}

export function patch<T>(path: string, body: unknown): Promise<T> {
  return fetchApi<T>(path, { method: "PATCH", body: JSON.stringify(body) });
}

export function del<T>(path: string): Promise<T> {
  return fetchApi<T>(path, { method: "DELETE" });
}

export function delWithBody<T>(path: string, body: unknown): Promise<T> {
  return fetchApi<T>(path, { method: "DELETE", body: JSON.stringify(body) });
}

/** Unwrap paginated responses that may be `{ items: T[] }` or plain `T[]`. */
export function unwrapItems<T>(res: { items: T[] } | T[]): T[] {
  return Array.isArray(res) ? res : (res.items ?? []);
}

/** Build a WebSocket URL for the project event stream. */
export function getWsUrl(projectId: string, token?: string): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const base = `${proto}//${window.location.host}/api/ws/events/${projectId}`;
  return token ? `${base}?token=${encodeURIComponent(token)}` : base;
}

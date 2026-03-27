/**
 * WebSocket event stream hook.
 *
 * Connects to project-scoped WebSocket endpoint, parses events,
 * and invalidates relevant query caches.
 * Reconnects automatically with exponential backoff on error.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { projectQueryPrefix } from "@/lib/query-keys";

import type { ConnectionState } from "@/types/events";
import type { SSEMessage } from "@/types/events";

interface UseEventStreamOptions {
  projectId?: string;
  sessionId?: string;
  enabled?: boolean;
}

const MAX_RECONNECT_DELAY_MS = 30_000;
const BASE_RECONNECT_DELAY_MS = 1_000;

/**
 * Parse the raw event data string from a WebSocket message
 * into an SSEMessage object.
 */
function parseSSEData(data: string): SSEMessage | null {
  try {
    return JSON.parse(data) as SSEMessage;
  } catch {
    return null;
  }
}

/**
 * Batched invalidation to prevent thundering herd during active workflows.
 * Accumulates query keys over a 1.5s window, then invalidates once per key.
 */
const INVALIDATION_DELAY_MS = 1_500;
let pendingInvalidation: ReturnType<typeof setTimeout> | null = null;
const pendingKeys = new Set<string>();
const pendingSessionIds = new Set<string>();
let pendingClient: QueryClient | null = null;
let pendingProjectId: string | null = null;

function flushInvalidation() {
  if (!pendingInvalidation) return;
  clearTimeout(pendingInvalidation);
  pendingInvalidation = null;
  if (!pendingClient || !pendingProjectId) {
    pendingKeys.clear();
    pendingSessionIds.clear();
    return;
  }
  const prefix = projectQueryPrefix(pendingProjectId);
  for (const serialized of pendingKeys) {
    const segments: string[] = JSON.parse(serialized);
    pendingClient.invalidateQueries({ queryKey: [...prefix, ...segments] });
  }
  for (const sid of pendingSessionIds) {
    pendingClient.invalidateQueries({
      queryKey: [...prefix, "sessions", "detail", sid],
    });
  }
  pendingKeys.clear();
  pendingSessionIds.clear();
}

function scheduleInvalidation(
  queryClient: QueryClient,
  projectId: string,
  keys: string[][],
  sessionIds?: string[],
) {
  pendingClient = queryClient;
  pendingProjectId = projectId;
  for (const k of keys) pendingKeys.add(JSON.stringify(k));
  if (sessionIds) {
    for (const sid of sessionIds) pendingSessionIds.add(sid);
  }
  if (pendingInvalidation) return; // already scheduled
  pendingInvalidation = setTimeout(flushInvalidation, INVALIDATION_DELAY_MS);
}

/**
 * Invalidate query caches selectively based on event type.
 * All keys are now project-scoped. Invalidations are batched over a 1.5s window.
 */
function invalidateForEvent(
  queryClient: QueryClient,
  message: SSEMessage,
  projectId: string,
): void {
  const eventType = message.event_type;

  // Defensive check for missing event_type (e.g., malformed messages)
  if (!eventType) {
    console.warn("WS message missing event_type:", message);
    scheduleInvalidation(queryClient, projectId, [
      ["features"],
      ["epics"],
      ["roadmaps"],
    ]);
    return;
  }

  const keys: string[][] = [];
  const sessionIds: string[] = [];

  // Session-scoped events: invalidate session detail + list
  if (eventType.startsWith("task_") || eventType.startsWith("session_")) {
    keys.push(["views", "factory-home"], ["sessions"]);
    if (message.session_id) {
      sessionIds.push(message.session_id);
    }
  }

  // Domain-specific invalidations
  if (eventType.startsWith("gate_")) {
    keys.push(["views", "gate-inbox"], ["gates"]);
  } else if (eventType === "entity_status_changed") {
    keys.push(["features"], ["epics"], ["roadmaps"], ["views"]);
  } else if (eventType.startsWith("feature_")) {
    keys.push(
      ["features"],
      ["views", "factory-home"],
      ["views", "features"],
      ["views", "epics"],
      ["views", "roadmaps"],
    );
  } else if (eventType.startsWith("epic_")) {
    keys.push(["epics"], ["views", "epics"], ["views", "roadmaps"]);
  } else if (
    eventType.startsWith("roadmap_") ||
    eventType === "milestone_created"
  ) {
    keys.push(["roadmaps"], ["views", "roadmaps"]);
  } else if (eventType === "autonomy_changed") {
    keys.push(["features"], ["epics"], ["control"]);
  } else if (eventType.startsWith("recovery_")) {
    keys.push(["views", "recovery-lab"], ["recovery"]);
  } else if (
    eventType.startsWith("artifact_") ||
    eventType.startsWith("frozen_artifact_")
  ) {
    keys.push(["artifacts"]);
  } else if (eventType.startsWith("contract_")) {
    keys.push(["views", "gate-inbox"]);
  }

  // Always update events and dashboard (batched with the rest)
  keys.push(["events"], ["dashboard"]);

  scheduleInvalidation(queryClient, projectId, keys, sessionIds);
}

/**
 * Hook for connecting to the event stream via WebSocket.
 * Reconnects with exponential backoff on failure.
 */
export function useEventStream(
  options: UseEventStreamOptions = {},
): ConnectionState {
  const { projectId, sessionId, enabled = true } = options;

  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = useRef(0);
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionState>("disconnected");

  const cleanup = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    flushInvalidation();
  }, []);

  useEffect(() => {
    if (!enabled || !projectId) {
      cleanup();
      setConnectionStatus("disconnected");
      attemptRef.current = 0;
      return;
    }

    function handleMessage(data: string) {
      const message = parseSSEData(data);
      if (message && projectId) {
        if ((message as any).type === "ping") return;
        invalidateForEvent(queryClient, message, projectId);
      }
    }

    function scheduleReconnect() {
      const attempt = attemptRef.current;
      attemptRef.current = attempt + 1;
      const delay = Math.min(
        BASE_RECONNECT_DELAY_MS * Math.pow(2, attempt),
        MAX_RECONNECT_DELAY_MS,
      );
      setConnectionStatus("reconnecting");
      reconnectTimerRef.current = setTimeout(connect, delay);
    }

    async function connect() {
      cleanup();

      const isReconnect = attemptRef.current > 0;
      setConnectionStatus(isReconnect ? "reconnecting" : "connecting");

      try {
        const res = await fetch("/api/auth/refresh", {
          method: "POST",
          credentials: "include",
        });
        if (!res.ok) {
          scheduleReconnect();
          return;
        }
        const data = await res.json();
        const token = data.token;
        if (!token) {
          scheduleReconnect();
          return;
        }

        const { getWsUrl } = await import("@/lib/api");
        const wsUrl = getWsUrl(projectId!, token);

        const ws = new WebSocket(wsUrl);
        const connectTimeout = setTimeout(() => {
          ws.close();
          scheduleReconnect();
        }, 5000);

        ws.onopen = () => {
          clearTimeout(connectTimeout);
          wsRef.current = ws;
          attemptRef.current = 0;
          setConnectionStatus("connected");

          // Subscribe to session-specific events if a sessionId is provided
          if (sessionId) {
            ws.send(JSON.stringify({ subscribe: sessionId }));
          }
        };

        ws.onmessage = (event) => {
          handleMessage(event.data);
        };

        ws.onerror = () => {
          clearTimeout(connectTimeout);
          ws.close();
          wsRef.current = null;
        };

        ws.onclose = () => {
          wsRef.current = null;
          if (connectionStatus === "connected") {
            scheduleReconnect();
          }
        };
      } catch {
        scheduleReconnect();
      }
    }

    connect();

    return cleanup;
  }, [sessionId, enabled, projectId, queryClient, cleanup]);

  return connectionStatus;
}

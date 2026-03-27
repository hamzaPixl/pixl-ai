/**
 * Hook for streaming session trace events with SDK-level detail.
 *
 * Loads historical events from the REST API on mount, then optionally
 * connects to the project WebSocket for live updates.
 * Deduplicates WS events against already-loaded DB events.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { SSEEventData, SDKEventData, TaskEventData } from "@/types/events";

const MAX_EVENTS = 2000;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

export type TraceEvent = (SDKEventData | TaskEventData) & {
  id: string;
  timestamp: Date;
};

export type ConnectionState = "disconnected" | "connecting" | "connected" | "reconnecting";

interface UseSessionTraceReturn {
  events: TraceEvent[];
  isConnected: boolean;
  connectionState: ConnectionState;
  isLoadingHistory: boolean;
  clear: () => void;
}

/**
 * Normalize a REST API event (raw DB row) to the same TraceEvent shape
 * that live events produce. Replicates backend _flatten_event_payload:
 * merges payload fields into root, then overlays event-level fields.
 */
function normalizeRestEvent(restEvent: Record<string, unknown>): TraceEvent {
  const dbId = restEvent.id as number;
  const payload = (restEvent.payload as Record<string, unknown>) || {};

  // Replicate backend _flatten_event_payload: {...event, ...payload}
  // Event fields take precedence over payload fields.
  const flattened = { ...restEvent, ...payload };

  return {
    ...flattened,
    id: `db-${dbId}`,
    timestamp: new Date(restEvent.created_at as string),
  } as TraceEvent;
}

function isRelevantEvent(eventType: string): boolean {
  return (
    eventType.startsWith("task_") ||
    eventType.startsWith("sdk_") ||
    eventType.startsWith("structured_output_") ||
    eventType.startsWith("gate_") ||
    eventType.startsWith("recovery_") ||
    eventType.startsWith("contract_") ||
    eventType === "git_unavailable"
  );
}

export function useSessionTrace(
  sessionId: string | null,
  isLive: boolean = true,
  projectId?: string | null,
): UseSessionTraceReturn {
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const eventCounterRef = useRef(0);
  // Track the max DB event ID for dedup against live events
  const lastDbEventIdRef = useRef(0);
  const historyLoadedRef = useRef(false);

  const clear = useCallback(() => {
    setEvents([]);
    eventCounterRef.current = 0;
    lastDbEventIdRef.current = 0;
    historyLoadedRef.current = false;
  }, []);

  const connect = useCallback(() => {
    if (!projectId || !sessionId) return;

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnectionState("connecting");

    async function doConnect() {
      try {
        // Fetch a fresh token for the WebSocket connection
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
          reconnectAttemptRef.current = 0;
          setConnectionState("connected");

          // Subscribe to session-specific events
          ws.send(JSON.stringify({ subscribe: sessionId }));
        };

        ws.onmessage = (event) => {
          try {
            const data: SSEEventData = JSON.parse(event.data);

            // Skip pings
            if ((data as any).type === "ping") return;

            // Only process relevant events
            if (!isRelevantEvent(data.event_type)) return;

            // Dedup: skip events we already loaded from the REST API
            const dbId = (data as any).id;
            if (typeof dbId === "number" && dbId > 0 && dbId <= lastDbEventIdRef.current) {
              return;
            }

            const traceEvent: TraceEvent = {
              ...data,
              id: `ws-${eventCounterRef.current++}`,
              timestamp: new Date(data.created_at),
            } as TraceEvent;

            setEvents((prev) => {
              const updated = [...prev, traceEvent];
              if (updated.length > MAX_EVENTS) {
                return updated.slice(-MAX_EVENTS);
              }
              return updated;
            });
          } catch (err) {
            console.error("Failed to parse WS event:", err);
          }
        };

        ws.onerror = () => {
          clearTimeout(connectTimeout);
          ws.close();
          wsRef.current = null;
        };

        ws.onclose = () => {
          wsRef.current = null;
          scheduleReconnect();
        };
      } catch {
        scheduleReconnect();
      }
    }

    function scheduleReconnect() {
      const delay = Math.min(
        RECONNECT_BASE_MS * Math.pow(2, reconnectAttemptRef.current),
        RECONNECT_MAX_MS,
      );
      reconnectAttemptRef.current++;
      setConnectionState("reconnecting");

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, delay);
    }

    doConnect();
  }, [projectId, sessionId]);

  useEffect(() => {
    if (!sessionId || !projectId) return;

    let cancelled = false;

    async function loadHistory() {
      setIsLoadingHistory(true);
      try {
        // api.events.list returns Event[] but actual response is raw DB rows
        const rawEvents = await api.events.list({ session_id: sessionId! });

        if (cancelled) return;

        const traceEvents: TraceEvent[] = [];
        let maxDbId = 0;

        for (const evt of rawEvents) {
          const raw = evt as unknown as Record<string, unknown>;
          const dbId = (raw.id as number) || 0;
          if (dbId > maxDbId) maxDbId = dbId;

          const eventType = (raw.event_type as string) || "";
          if (!isRelevantEvent(eventType)) continue;

          traceEvents.push(normalizeRestEvent(raw));
        }

        lastDbEventIdRef.current = maxDbId;
        historyLoadedRef.current = true;

        if (traceEvents.length > 0) {
          setEvents(traceEvents.slice(-MAX_EVENTS));
        }
      } catch (err) {
        console.error("Failed to load historical events:", err);
        // Still allow WS to connect even if history load fails
        historyLoadedRef.current = true;
      } finally {
        if (!cancelled) {
          setIsLoadingHistory(false);
        }
      }
    }

    loadHistory();

    return () => {
      cancelled = true;
    };
  }, [sessionId, projectId]);

  // Connect WS when isLive and history has finished loading.
  const historyReady = !isLoadingHistory && historyLoadedRef.current;

  useEffect(() => {
    if (sessionId && isLive && historyReady) {
      connect();
    }

    // If not live, close WS connection
    if (!isLive && wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
      setConnectionState("disconnected");
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [sessionId, isLive, historyReady, connect]);

  return {
    events,
    isConnected: connectionState === "connected",
    connectionState,
    isLoadingHistory,
    clear,
  };
}

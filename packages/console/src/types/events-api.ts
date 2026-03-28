import type { EventType } from "./enums";

export interface Event {
  id: string; // evt-XXXXXXXXXXXX
  type: EventType;
  timestamp: string;
  session_id: string;
  node_id: string | null;
  artifact_id: string | null;
  data: Record<string, unknown>;
}

export interface TransitionRecord {
  id: number;
  entity_id: string;
  entity_type: string;
  from_status: string | null;
  to_status: string;
  triggered_by: string | null;
  created_at: string;
}

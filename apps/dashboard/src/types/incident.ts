import { EventSeverity, SurveillanceEvent } from './event';

/** Supabase DB status values (uppercase) + legacy WS values (lowercase) */
export type IncidentStatus =
  | 'OPEN'
  | 'ACKNOWLEDGED'
  | 'RESOLVED'
  | 'FALSE_POSITIVE'
  | 'DISMISSED'
  // Legacy lowercase values from in-memory/WS shape
  | 'active'
  | 'acknowledged'
  | 'investigating'
  | 'resolved'
  | 'false_alarm';

/** Contributing event in an incident (from incident_events JOIN events) */
export interface IncidentContributingEvent {
  incident_id: string;
  event_id: string;
  contribution_score: number;
  is_primary: boolean;
  events?: SurveillanceEvent;
}

export interface Incident {
  // DB fields
  id?: string;
  incident_code?: string;
  incident_type?: string;
  created_at?: string;
  updated_at?: string;
  first_event_ts?: string | number | null;
  last_event_ts?: string | number | null;
  incident_events?: IncidentContributingEvent[];
  title?: string;
  acknowledged_by?: string | null;

  // Legacy / WS fields
  incident_id?: string; // Optional because DB uses id
  track_id?: number;
  risk_score: number;
  severity: EventSeverity | string;
  triggering_events?: SurveillanceEvent[];
  timestamp?: number; // Unix timestamp for legacy
  camera_name?: string;
  camera_id?: string;
  description?: string;
  status?: IncidentStatus;
  acknowledged_at?: string | number | null;
  blockchain_tx_hash?: string;
  evidence_hash?: string;
}

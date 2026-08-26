import { EventSeverity, SurveillanceEvent } from './event';

export type IncidentStatus = 'active' | 'investigating' | 'acknowledged' | 'resolved' | 'false_alarm';

export interface Incident {
  incident_id: string;
  track_id: number;
  risk_score: number;
  severity: EventSeverity;
  triggering_events: SurveillanceEvent[];
  timestamp: number; // Unix timestamp
  camera_name?: string;
  camera_id?: string;
  description?: string;
  status?: IncidentStatus;
  acknowledged_at?: number | null;
  acknowledged_by?: string | null;
}

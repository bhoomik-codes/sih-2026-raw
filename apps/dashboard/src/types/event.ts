export type EventType =
  | 'ZONE_ENTRY'
  | 'ZONE_EXIT'
  | 'LINE_CROSSING'
  | 'LOITERING'
  | 'WRONG_DIRECTION'
  | 'VEHICLE_ANPR'
  | 'FACE_DETECTED'
  | 'UNKNOWN';

export type EventSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface SurveillanceEvent {
  event_id?: string;
  event_type: EventType;
  severity: EventSeverity;
  track_id: number;
  camera_name?: string;
  camera_id?: string;
  timestamp: number; // Unix timestamp in seconds or milliseconds
  frame_id?: number;
  location?: [number, number]; // [x, y]
  class_name?: string;
  confidence?: number;
  rule_name?: string;
  details?: Record<string, any>;
  capture_ts?: string;
  ingest_ts?: string;
  display_ts?: string;
  // DB fields
  id?: string;
  event_code?: string;
  event_ts?: string | number;
  status?: string;
  bbox_x1?: number;
  bbox_y1?: number;
  bbox_x2?: number;
  bbox_y2?: number;
  metadata?: Record<string, any>;
}

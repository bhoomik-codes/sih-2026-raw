export type EventSeverity = 'low' | 'medium' | 'high' | 'critical';

export type EventType =
  | 'ZONE_ENTRY'
  | 'ZONE_EXIT'
  | 'LINE_CROSSING'
  | 'LOITERING'
  | 'WRONG_DIRECTION'
  | 'ANPR_FLAGGED'
  | 'FACE_MATCH'
  | 'BORDER_INTRUSION'
  | 'UNKNOWN';

export interface Detection {
  id: number;
  class_name: 'person' | 'car' | 'truck' | 'motorcycle' | 'bus' | 'drone' | 'animal';
  confidence: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
  velocity?: [number, number]; // [vx, vy]
  track_history?: [number, number][]; // past centroid positions
  is_flagged?: boolean;
  attributes?: {
    carrying_backpack?: boolean;
    crawling?: boolean;
    speed_kmh?: number;
    license_plate?: string;
    matched_identity?: string;
  };
}

export interface SurveillanceEvent {
  event_id: string;
  event_type: EventType;
  severity: EventSeverity;
  track_id: number;
  camera_id: string;
  camera_name: string;
  timestamp: number; // Unix epoch ms
  frame_id: number;
  location: [number, number]; // [x, y] in frame coordinates
  class_name: string;
  confidence: number;
  rule_name: string;
  details?: Record<string, any>;
  capture_ts: string;
  ingest_ts: string;
  display_ts: string;
}

export interface Incident {
  id: string;
  title: string;
  severity: EventSeverity;
  status: 'active' | 'investigating' | 'dispatched' | 'resolved' | 'false_alarm';
  risk_score: number; // 0 - 100
  camera_id: string;
  camera_name: string;
  sector: string;
  created_at: number;
  updated_at: number;
  primary_event: SurveillanceEvent;
  contributing_events: string[];
  explainability: {
    rule_triggers: string[];
    risk_factors: {
      factor: string;
      weight: number;
      description: string;
    }[];
    spatial_summary: string;
    temporal_summary: string;
    recommendation: string;
  };
  snapshot_url?: string;
  assigned_patrol?: string;
  notes?: string[];
}

export interface CameraZone {
  name: string;
  polygon: [number, number][]; // normalized or pixel coordinates
  classes: string[];
  severity: EventSeverity;
  type: 'restricted' | 'loitering' | 'buffer';
  threshold_s?: number;
}

export interface VirtualFenceLine {
  name: string;
  start: [number, number];
  end: [number, number];
  direction: 'AB' | 'BA' | 'any';
  classes: string[];
  severity: EventSeverity;
}

export interface CameraFeed {
  id: string;
  name: string;
  sector: string;
  location_name: string;
  lat: number;
  lng: number;
  fov_heading: number; // degrees 0-360
  fov_angle: number; // degrees (e.g. 60)
  status: 'online' | 'degraded' | 'offline';
  fps: number;
  resolution: string;
  bitrate_mbps: number;
  feed_type: 'rgb' | 'thermal' | 'ptz' | 'drone';
  stream_url?: string;
  detections: Detection[];
  zones: CameraZone[];
  lines: VirtualFenceLine[];
  thermal_mode?: 'white-hot' | 'ironbow' | 'rainbow';
  is_recording?: boolean;
}

export interface Telemetry {
  gpu: {
    name: string;
    utilization_pct: number;
    vram_used_gb: number;
    vram_total_gb: number;
    temperature_c: number;
    power_watts: number;
  };
  edge_node: {
    hostname: string;
    inference_fps: number;
    pipeline_latency_ms: number;
    queue_depth: number;
    dropped_frames_pct: number;
    uptime_seconds: number;
    status: 'OPTIMAL' | 'DEGRADED' | 'WARNING';
  };
  operator_station: {
    cpu_usage_pct: number;
    ram_used_gb: number;
    ram_total_gb: number;
    ws_roundtrip_ms: number;
  };
}

export interface ANPRRecord {
  id: string;
  plate_number: string;
  camera_id: string;
  camera_name: string;
  timestamp: number;
  vehicle_type: string;
  vehicle_color: string;
  confidence: number;
  is_blacklisted: boolean;
  blacklist_reason?: string;
  snapshot_url?: string;
}

export interface PatrolUnit {
  id: string;
  callsign: string;
  personnel_count: number;
  status: 'patrolling' | 'responding' | 'standby' | 'out_of_area';
  lat: number;
  lng: number;
  eta_minutes?: number;
  assigned_incident_id?: string;
}

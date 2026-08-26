export type CameraStatus = 'ONLINE' | 'OFFLINE' | 'CONNECTING' | 'ERROR';
export type CameraSourceType = 'rtsp' | 'http' | 'mjpeg' | 'file' | 'webcam';

export interface CameraLocation {
  lat: number | null;
  lng: number | null;
}

export interface Zone {
  name: string;
  polygon: [number, number][]; // [[x, y], ...]
  classes?: string[];
  severity?: 'low' | 'medium' | 'high' | 'critical';
  type?: 'restricted' | 'loitering' | 'buffer';
  threshold_s?: number;
}

export interface FenceLine {
  name: string;
  start: [number, number]; // [x, y]
  end: [number, number];   // [x, y]
  direction?: 'AB' | 'BA' | 'any';
  classes?: string[];
  severity?: 'low' | 'medium' | 'high' | 'critical';
}

export interface Camera {
  camera_id: string;
  name: string;
  source_url: string;
  source_type: CameraSourceType;
  status: CameraStatus;
  location?: CameraLocation;
  inference_enabled: boolean;
  stream_url?: string;
  zones?: Zone[];
  lines?: FenceLine[];
  fps?: number;
  resolution?: string;
  bitrate_mbps?: number;
}

export interface CameraCreatePayload {
  camera_id: string;
  name: string;
  source_url: string;
  source_type: CameraSourceType;
  location?: CameraLocation;
  inference_enabled?: boolean;
}

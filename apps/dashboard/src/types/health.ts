export type HealthStatusLevel = 'ONLINE' | 'CONNECTING' | 'OFFLINE' | 'DEGRADED';

export interface SystemHealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy' | string;
  edge_node_connected: boolean;
  active_cameras: number;
  uptime_seconds?: number;
  details?: Record<string, any>;
}

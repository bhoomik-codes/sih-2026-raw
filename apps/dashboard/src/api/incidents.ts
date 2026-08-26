import { apiRequest } from './client';
import { Incident } from '../types/incident';

export interface GetIncidentsParams {
  severity?: string;
  camera_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export async function getIncidents(params: GetIncidentsParams = {}): Promise<Incident[]> {
  const query = new URLSearchParams();
  if (params.severity) query.set('severity', params.severity);
  if (params.camera_id) query.set('camera_id', params.camera_id);
  if (params.status) query.set('status', params.status);
  if (params.limit !== undefined) query.set('limit', params.limit.toString());
  if (params.offset !== undefined) query.set('offset', params.offset.toString());

  const qs = query.toString();
  return apiRequest<Incident[]>(`/api/incidents${qs ? `?${qs}` : ''}`);
}

export async function getIncident(id: string): Promise<Incident> {
  return apiRequest<Incident>(`/api/incidents/${encodeURIComponent(id)}`);
}

export async function acknowledgeIncident(id: string): Promise<Incident> {
  return apiRequest<Incident>(`/api/incidents/${encodeURIComponent(id)}/acknowledge`, {
    method: 'POST',
  });
}

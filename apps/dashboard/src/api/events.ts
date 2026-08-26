import { apiRequest } from './client';
import { SurveillanceEvent } from '../types/event';

export interface GetEventsParams {
  camera_id?: string;
  limit?: number;
  offset?: number;
}

export async function getEvents(params: GetEventsParams = {}): Promise<SurveillanceEvent[]> {
  const query = new URLSearchParams();
  if (params.camera_id) query.set('camera_id', params.camera_id);
  if (params.limit !== undefined) query.set('limit', params.limit.toString());
  if (params.offset !== undefined) query.set('offset', params.offset.toString());

  const qs = query.toString();
  return apiRequest<SurveillanceEvent[]>(`/api/events${qs ? `?${qs}` : ''}`);
}

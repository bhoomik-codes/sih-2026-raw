import { apiRequest } from './client';
import { SystemHealthResponse } from '../types/health';

export async function getHealth(): Promise<SystemHealthResponse> {
  return apiRequest<SystemHealthResponse>('/api/health');
}

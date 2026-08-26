import { apiRequest } from './client';
import { SystemMetrics } from '../types/metrics';

export async function getMetrics(): Promise<SystemMetrics> {
  return apiRequest<SystemMetrics>('/api/metrics');
}

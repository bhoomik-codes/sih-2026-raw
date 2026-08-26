import { apiRequest } from './client';
import { Camera, CameraCreatePayload, Zone, FenceLine } from '../types/camera';

export async function getCameras(): Promise<Camera[]> {
  return apiRequest<Camera[]>('/api/cameras');
}

export async function getCamera(id: string): Promise<Camera> {
  return apiRequest<Camera>(`/api/cameras/${encodeURIComponent(id)}`);
}

export async function createCamera(payload: CameraCreatePayload): Promise<Camera> {
  return apiRequest<Camera>('/api/cameras', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function deleteCamera(id: string): Promise<void> {
  return apiRequest<void>(`/api/cameras/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

export async function startCamera(id: string): Promise<{ success: boolean; message?: string }> {
  return apiRequest<{ success: boolean; message?: string }>(`/api/cameras/${encodeURIComponent(id)}/start`, {
    method: 'POST',
  });
}

export async function stopCamera(id: string): Promise<{ success: boolean; message?: string }> {
  return apiRequest<{ success: boolean; message?: string }>(`/api/cameras/${encodeURIComponent(id)}/stop`, {
    method: 'POST',
  });
}

export async function reconnectCamera(id: string): Promise<{ success: boolean; message?: string }> {
  return apiRequest<{ success: boolean; message?: string }>(`/api/cameras/${encodeURIComponent(id)}/reconnect`, {
    method: 'POST',
  });
}

export async function updateCameraZones(id: string, zones: Zone[]): Promise<Camera> {
  return apiRequest<Camera>(`/api/cameras/${encodeURIComponent(id)}/zones`, {
    method: 'POST',
    body: JSON.stringify({ zones }),
  });
}

export async function updateCameraFence(id: string, lines: FenceLine[]): Promise<Camera> {
  return apiRequest<Camera>(`/api/cameras/${encodeURIComponent(id)}/fence`, {
    method: 'POST',
    body: JSON.stringify({ lines }),
  });
}

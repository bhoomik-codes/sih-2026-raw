import { apiRequest } from './client';
import { FaceRecord, CreateFacePayload, UpdateFacePayload } from '../types/face';

/** Fetch all face records (thumbnails included, embeddings excluded) */
export async function getFaces(): Promise<FaceRecord[]> {
  return apiRequest<FaceRecord[]>('/api/faces');
}

/** Create a new face record — image_b64 is sent for embedding computation */
export async function createFace(payload: CreateFacePayload): Promise<FaceRecord> {
  return apiRequest<FaceRecord>('/api/faces', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/** Update name, role, or notes for an existing face record */
export async function updateFace(id: string, patch: UpdateFacePayload): Promise<FaceRecord> {
  return apiRequest<FaceRecord>(`/api/faces/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(patch),
  });
}

/** Delete a face record by ID */
export async function deleteFace(id: string): Promise<void> {
  return apiRequest<void>(`/api/faces/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

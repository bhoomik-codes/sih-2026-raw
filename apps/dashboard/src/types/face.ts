// Face Registry types for IBVAP Face Recognition System

export type FaceRole = 'SOLDIER' | 'INTRUDER';

export interface FaceRecord {
  id: string;
  name: string;
  role: FaceRole;
  /** Base64-encoded JPEG/PNG thumbnail (returned by backend without full embedding) */
  image_b64?: string;
  created_at: string;
  updated_at?: string;
  /** Optional notes/rank/unit */
  notes?: string;
}

export interface CreateFacePayload {
  name: string;
  role: FaceRole;
  /** Full base64-encoded image for embedding computation */
  image_b64: string;
  notes?: string;
}

export interface UpdateFacePayload {
  name?: string;
  role?: FaceRole;
  notes?: string;
}

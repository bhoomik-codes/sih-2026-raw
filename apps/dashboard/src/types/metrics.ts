export interface SystemMetrics {
  fps: number | null;
  inference_fps: number | null;
  inference_latency_ms: number | null;
  preprocess_latency_ms: number | null;
  total_latency_ms: number | null;
  queue_depth: number | null;
  dropped_frames: number | null;
  dropped_ratio: number | null;
  processed_frames: number | null;
  
  // Hardware metrics
  gpu_utilization_pct: number | null;
  vram_used_mb: number | null;
  vram_total_mb: number | null;
  gpu_temp_c: number | null;
  cpu_utilization_pct: number | null;
  ram_used_mb: number | null;
  ram_total_mb: number | null;

  // Status flags
  detector_status?: string | null;
  tracker_status?: string | null;
}

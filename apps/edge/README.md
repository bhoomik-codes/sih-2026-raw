# apps/edge — AI Edge Processing Node (Laptop 1)

> **Hardware target:** Laptop 1 — Intel i5 13th Gen · NVIDIA RTX 4050 6 GB VRAM

This is the AI inference node. It is the only component that touches GPU resources.

## Responsibilities

```
CCTV Camera (RTSP / local file)
         ↓
   VideoSource (video_source.py)
   - Thread-safe frame ingestion
   - RTSP watchdog + auto-reconnect
   - Latest-frame bounded queue (prevents latency buildup)
         ↓
   Preprocessing (cv/preprocessing/)
   - Resize to inference resolution
   - Optional ROI masking
         ↓
   Perception Engine (cv/detection/, cv/tracking/)
   - Object detection (YOLOv8 via YOLODetector)
   - Multi-object tracking (Phase 2: ByteTrack/BoT-SORT)
         ↓
   Event Engine (intelligence/events/) — Phase 3
   - Virtual fence / line crossing
   - Loitering detection
   - Direction detection
         ↓
   Risk & Incident Engine (intelligence/) — Phase 4
   - Event correlation
   - Risk scoring
   - Incident generation
         ↓
   Metrics + Event Publisher
   - Emits structured events over WebSocket to apps/backend/
   - Exposes /health and /metrics endpoints
```

## Running

```bash
# Standard run (displays annotated video window)
python -m apps.edge.main --config configs/phase1_default.yaml

# Headless — for remote/SSH sessions
python -m apps.edge.main --config configs/phase1_default.yaml --no-display

# Override camera source at CLI
python -m apps.edge.main --config configs/phase1_default.yaml \
    --source rtsp://192.168.1.10:554/stream
```

## Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point |
| `video_source.py` | Thread-safe camera/RTSP reader |
| `processor.py` | Main inference loop |
| `metrics.py` | GPU/CPU/FPS metrics collection |

## What This Node Does NOT Do

- **No UI** — display window is development-only; removed for demo
- **No database writes** — events go via WebSocket to `apps/backend/`
- **No HTTP serving** — the backend handles that

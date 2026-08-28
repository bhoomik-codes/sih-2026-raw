# apps/edge — Edge AI Inference & Processing Node (Laptop 1)

> **Status:** Production Ready (Phases 1–8 Complete)  
> **Hardware target:** Laptop 1 — Intel i5 13th Gen · NVIDIA RTX 4050 6 GB VRAM

The Edge Node is the dedicated GPU compute worker in the IBVAP architecture. It ingests live video streams, executes high-throughput neural detection, runs multi-object tracking, calculates spatial threat rules, serves local MJPEG video feeds, and streams structured events to the Command Center backend.

---

## 🏗️ Edge Processing Loop

```
  Camera / Video Source (RTSP / .mp4 / USB / GStreamer)
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                 apps/edge/processor.py                      │
│                                                             │
│  1. Video Ingestion (`apps/edge/video_source.py`)           │
│     - Thread-safe bounded queue (drops stale frames)        │
│     - Active RTSP watchdog with auto-reconnect              │
│                                                             │
│  2. Frame Preprocessing (`cv/preprocessing/frame_prep.py`)   │
│     - Dynamic low-light CLAHE contrast boost                │
│     - Optional polygon ROI masking & letterbox scaling      │
│                                                             │
│  3. Neural Detection (`cv/detection/`)                      │
│     - YOLOv8 (PyTorch / ONNX Runtime / TensorRT)            │
│     - Configurable N-frame skip inference                   │
│                                                             │
│  4. Multi-Object Tracking (`cv/tracking/byte_tracker.py`)   │
│     - ByteTrack Kalman filter tracking                      │
│     - Persistent track IDs with TTL trajectory garbage coll.│
│                                                             │
│  5. Threat Rules & Intelligence (`intelligence/`)           │
│     - Virtual Fence & Line Crossing checks                  │
│     - Dwell-time loitering & Night activity triggers        │
│     - ANPR plate crop buffer & OCR scheduling               │
│     - Cumulative multi-event Risk Scoring                   │
│                                                             │
│  6. MJPEG Video Streamer (`apps/edge/streamer.py`)          │
│     - Background HTTP server (port 8081+)                   │
│     - Encodes real-time HUD annotations for browser feeds   │
│                                                             │
│  7. Event Transmitter (`apps/edge/transmitter.py`)          │
│     - Non-blocking queue to `ws://localhost:8000/ws`        │
│     - Auto-reconnecting background worker                   │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚡ CLI Usage & Commands

```bash
# Activate virtual environment
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate

# 1. Single camera run with live video streaming on port 8081
python -m apps.edge.main \
  --config configs/phase1_default.yaml \
  --source data/videos/border_crossing_test.mp4 \
  --stream-port 8081

# 2. Headless mode (no local OpenCV GUI window, only HTTP streaming)
python -m apps.edge.main \
  --config configs/phase1_default.yaml \
  --no-display \
  --stream-port 8081

# 3. ONNX Runtime backend (Phase 7)
python -m apps.edge.main \
  --config configs/phase7_default.yaml \
  --stream-port 8081

# 4. Multi-camera concurrent supervisor (Phase 8)
python -m apps.edge.multi_main \
  --config configs/phase8_default.yaml
```

---

## 📂 Key Files

| Module | Description |
| :--- | :--- |
| `main.py` | CLI entry point for single-camera edge node with runtime overrides. |
| `multi_main.py` | Supervisor managing concurrent worker threads across multiple cameras. |
| `processor.py` | Central processing loop coordinating CV, tracking, intelligence, and streaming. |
| `streamer.py` | Zero-overhead HTTP MJPEG video streamer for web dashboards. |
| `transmitter.py` | Non-blocking background WebSocket client transmitting events to backend. |
| `video_source.py` | Threaded video reader with hardware watchdog and ring-buffer queue. |
| `metrics.py` | Telemetry recorder for rolling FPS, GPU VRAM, and pipeline latencies. |

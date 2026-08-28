# IBVAP — Developer & Architecture Guide
**Intelligent Border Video Analytics Platform (SIH 2026)**

Welcome to the comprehensive developer documentation for the Intelligent Border Video Analytics Platform (IBVAP). This guide provides engineers with an end-to-end understanding of the system architecture, mathematical data flows, codebase organization, setup workflows, and extension patterns.

---

## 1. System Architecture & Topology

IBVAP is built as a distributed, edge-native surveillance and threat intelligence platform optimized for low-latency border security operations on commodity edge hardware.

```
+-----------------------------------------------------------------------------------+
|                            LAPTOP 1: EDGE AI NODE                                 |
|                                                                                   |
|  +-------------------+      +-------------------+      +-----------------------+  |
|  | Video Ingestion   | ---> | CPU Preprocessing | ---> | YOLOv8 / ONNX / TRT   |  |
|  | (OpenCV / GStream)|      | (ROI / CLAHE)     |      | Object Detector       |  |
|  +-------------------+      +-------------------+      +-----------------------+  |
|                                                                    |              |
|  +-------------------+      +-------------------+                  v              |
|  | ANPR & OCR Engine | <--- | Risk Scorer &     | <--- +-----------------------+  |
|  | (CLAHE + PlateOCR)|      | Incident Generator|      | ByteTracker           |  |
|  +-------------------+      +-------------------+      | (Persistent IDs + TTL)|  |
|            |                          |                +-----------------------+  |
|            v                          v                            |              |
|  +----------------------------------------------+                  v              |
|  | Non-Blocking WebSocket EdgeTransmitter       | <--- +-----------------------+  |
|  | (`apps/edge/transmitter.py`)                 |      | Spatial Event Engine  |  |
|  +----------------------------------------------+      | (Fence/Crossing/Loiter|  |
|            |                          |                +-----------------------+  |
|            | ws://localhost:8000/ws   |                                           |
|            |                          v                                           |
|            |                +----------------------------------+                  |
|            |                | MJPEG Streamer (`streamer.py`)   |                  |
|            |                | (Port 8081+ HTTP Stream Server)  |                  |
|            |                +----------------------------------+                  |
+------------|-----------------------------------|----------------------------------+
             v                                   |
+------------------------------------------------|----------------------------------+
|                   LAPTOP 2 / SERVER: COMMAND CENTER & CLOUD                       |
|                                                |                                  |
|  +---------------------------------------------|-------------------------------+  |
|  | FastAPI Backend (`apps/backend/main.py`)    v                               |  |
|  | - Bi-directional `/ws` hub (Broadcasts to dashboard clients)                |  |
|  | - Stream reverse proxy (`/api/streams/{camera_id}`)                        |  |
|  | - REST API (`/api/cameras`, `/api/events`, `/api/incidents`, `/api/metrics`)|  |
|  | - Supabase PostgreSQL Data Access Layer (`apps/backend/db.py`)               |  |
|  +-----------------------------------------------------------------------------+  |
|               |                                                |                  |
|               v                                                v                  |
|  +---------------------------+                +--------------------------------+  |
|  | Supabase PostgreSQL DB    |                | React Command Center UI        |  |
|  | (17 Relational Tables     |                | (`apps/dashboard/`)            |  |
|  |  via Alembic Migrations)  |                | - Vite + React 18 + TypeScript |  |
|  +---------------------------+                | - Live MJPEG Video Stream Grid |  |
|                                               | - Explainability Risk Gauges   |  |
|                                               +--------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Directory Layout

```
sih-2026-raw/
├── alembic/                      # SQLAlchemy / Alembic database migration suite
│   ├── env.py                    # Migration runtime & .env connection loader
│   └── versions/                 # Versioned schema migrations
├── apps/
│   ├── backend/                  # FastAPI Command Center backend
│   │   ├── main.py               # REST endpoints, process manager, WebSocket hub, stream proxy
│   │   ├── db.py                 # Supabase & PostgreSQL client singleton
│   │   └── requirements.txt      # Backend Python dependencies
│   ├── dashboard/                # Command Center Web UI (Vite + React + TypeScript)
│   │   ├── src/
│   │   │   ├── components/       # LiveStream HUD, IncidentDetailModal, AlertToast, CameraGrid
│   │   │   ├── pages/            # CommandCenter, CameraManagement, Incidents, Map, Health
│   │   │   └── websocket/        # Real-time WebSocket hook (useWebSocket)
│   │   └── package.json          # Node.js dependencies
│   └── edge/                     # Edge AI inference node runtime
│       ├── main.py               # Single-camera Edge entry point & CLI
│       ├── multi_main.py         # Multi-camera concurrent supervisor
│       ├── processor.py          # Central inference, tracking, rules & streaming loop
│       ├── video_source.py       # Threaded OpenCV reader with watchdog protection
│       ├── multi_camera_manager.py # Multi-stream orchestration & health monitor
│       ├── transmitter.py        # Resilient background WebSocket edge transmitter
│       ├── streamer.py           # Zero-overhead MJPEG HTTP video server
│       └── metrics.py            # Rolling FPS and latency telemetry recorder
├── benchmarks/                   # GPU/CPU baseline performance benchmarks
├── configs/                      # Ready-to-use YAML configs for all operational phases
├── cv/                           # Pure Computer Vision algorithms
│   ├── anpr/                     # Plate preprocessor (CLAHE, bilateral) & PlateOCR
│   ├── detection/                # YOLOv8 PyTorch and ONNX Runtime backends
│   ├── face/                     # Checkpoint pedestrian face detector
│   ├── preprocessing/            # CPU-side frame resizing, ROI masking & low-light CLAHE
│   └── tracking/                 # ByteTracker with TTL trajectory memory management
├── docs/                         # Developer and architectural documentation
├── intelligence/                 # Threat Rules & Incident Scoring
│   ├── anpr/                     # High-level vehicle crop buffer & OCR scheduler
│   ├── events/                   # Spatial rules (Virtual Fence, Line Crossing, Loitering, Night)
│   ├── incidents/                # Incident generator with temporal cooldown & correlation
│   └── risk/                     # Multi-event cumulative risk scoring engine
├── models/                       # Model weight storage (.pt, .onnx, .engine)
├── pipelines/                    # Video ingestion pipeline backends (OpenCV, GStreamer, DeepStream)
├── scripts/                      # Utility scripts (download video, export ONNX, run demo)
├── tests/                        # 132 automated unit and integration tests
├── KNOWN_ISSUES.md               # Bug tracker and architectural resolutions
├── schema.md                     # Complete Supabase PostgreSQL relational schema
└── tasks.md                      # Milestone completion tracker
```

---

## 3. Core Subsystems & Data Flow

### 3.1 Computer Vision Layer (`cv/`)
- [cv/detection/base.py](file:///Users/apple/sih-2026-raw/cv/detection/base.py): Defines `BBox`, `Detection`, and `DetectorBase`.
- [cv/detection/yolo_detector.py](file:///Users/apple/sih-2026-raw/cv/detection/yolo_detector.py): PyTorch-based Ultralytics YOLOv8 detector with warm-up logic.
- [cv/detection/onnx_detector.py](file:///Users/apple/sih-2026-raw/cv/detection/onnx_detector.py): Standalone ONNX Runtime detector for edge platforms without PyTorch.
- [cv/tracking/byte_tracker.py](file:///Users/apple/sih-2026-raw/cv/tracking/byte_tracker.py): Two-stage Kalman-filtered ByteTrack tracker with TTL trajectory garbage collection.
- [cv/anpr/plate_pipeline.py](file:///Users/apple/sih-2026-raw/cv/anpr/plate_pipeline.py): Contrast enhancement, deskewing, and OCR extraction with `PlateOCR`.
- [cv/preprocessing/frame_prep.py](file:///Users/apple/sih-2026-raw/cv/preprocessing/frame_prep.py): ROI polygon masking, aspect ratio letterboxing, and low-light YCrCb CLAHE equalization.

### 3.2 Threat Intelligence & Risk Scorer (`intelligence/`)
- [intelligence/events/virtual_fence.py](file:///Users/apple/sih-2026-raw/intelligence/events/virtual_fence.py): Ray-casting polygon containment detection emitting `ZONE_ENTRY` / `ZONE_EXIT`.
- [intelligence/events/line_crossing.py](file:///Users/apple/sih-2026-raw/intelligence/events/line_crossing.py): Vector cross-product sign change detection (`A->B` or `B->A`) for perimeter breaches.
- [intelligence/events/loitering.py](file:///Users/apple/sih-2026-raw/intelligence/events/loitering.py): Dwell-time tracking using real Unix timestamps (FPS-independent).
- [intelligence/risk/scorer.py](file:///Users/apple/sih-2026-raw/intelligence/risk/scorer.py): Maps cumulative events to dynamic threat scores (0–100) and severity bands (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- [intelligence/incidents/generator.py](file:///Users/apple/sih-2026-raw/intelligence/incidents/generator.py): Escalates multi-event risk scores into correlated security incidents with temporal cooldowns.

### 3.3 Edge Ingestion & Video Streaming (`apps/edge/`)
- [apps/edge/processor.py](file:///Users/apple/sih-2026-raw/apps/edge/processor.py): Central loop coordinating video ingestion, inference, tracking, rules, HUD rendering, and streaming.
- [apps/edge/streamer.py](file:///Users/apple/sih-2026-raw/apps/edge/streamer.py): Multi-client HTTP MJPEG video streamer running on assigned ports (e.g. 8081).
- [apps/edge/transmitter.py](file:///Users/apple/sih-2026-raw/apps/edge/transmitter.py): Background queue-backed WebSocket client that auto-reconnects to the backend without blocking frame rates.

### 3.4 Command Center Backend & Dashboard (`apps/backend/` & `apps/dashboard/`)
- [apps/backend/main.py](file:///Users/apple/sih-2026-raw/apps/backend/main.py): FastAPI backend providing `/ws` broadcasting, stream proxies (`/api/streams/{id}`), local video serving (`/api/videos`), and REST APIs.
- [apps/backend/db.py](file:///Users/apple/sih-2026-raw/apps/backend/db.py): Supabase and PostgreSQL database adapter.
- [apps/dashboard/](file:///Users/apple/sih-2026-raw/apps/dashboard/): Tactical Command Center React UI with live camera matrix, explainability gauge modal, and alert toasts.

---

## 4. Quick Start & Execution

### 4.1 Prerequisites
- Python 3.11 or 3.12
- Node.js >= 18 and npm

### 4.2 Setup
```bash
git clone https://github.com/bhoomik-codes/sih-2026-raw.git
cd sih-2026-raw

python3 -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
pip install -e ".[dev]"

cd apps/dashboard && npm install && cd ../..
```

### 4.3 Launch the Full Platform
Run the multi-process launcher script:
```bash
python scripts/run_demo.py
```
Or start the components across individual terminals:
```bash
# Terminal 1: Backend
uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Dashboard UI
cd apps/dashboard && npm run dev

# Terminal 3: Edge AI Node with Video Streaming
python -m apps.edge.main --config configs/phase1_default.yaml --source data/videos/border_crossing_test.mp4 --stream-port 8081
```

---

## 5. Testing & Quality Assurance

All components are covered by 132 automated pytest unit tests:
```bash
# Run entire test suite
.venv/bin/pytest tests/ -v

# Run linting and style validation
.venv/bin/ruff check .
```

---

## 6. Architecture & Performance Rules

1. **Non-Blocking Ingestion**: Video reading and telemetry sending must never block the AI inference loop. Use `.get_nowait()` and bounded queue buffers.
2. **Garbage Collection of Tracking State**: Every engine tracking per-track state must implement `cleanup_stale_tracks(active_track_ids)` to prevent memory leaks during 24/7 continuous operation.
3. **Geometry > Heavy Neural Networks**: Utilize analytical geometry (raycasting, vector cross-products) for spatial reasoning instead of heavy classifiers.
4. **Decoupled Video Streams**: Video frames are served over lightweight MJPEG HTTP servers (`apps/edge/streamer.py`) while telemetry is streamed over WebSockets (`apps/edge/transmitter.py`).

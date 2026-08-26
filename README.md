# IBVAP — Intelligent Border Video Analytics Platform

**SIH 2026 · Problem Statement SIH26187**  
**Organization:** Ministry of Home Affairs / Sashastra Seema Bal

> Transform existing IP-based CCTV infrastructure into an AI-powered border surveillance
> platform — without expensive dedicated hardware.

---

## System Architecture

```
┌────────────────────────────────────┐
│         CCTV CAMERAS               │
│   RTSP / IP Stream / Local File    │
└────────────────┬───────────────────┘
                 │
                 ▼ LAN / Wi-Fi
┌────────────────────────────────────┐
│         LAPTOP 1                   │
│   Intel i5 13th Gen · RTX 4050     │
│                                    │
│   ┌──────────────────────────┐     │
│   │   apps/edge/             │     │  ← AI Edge Node (GPU)
│   │   AI Inference Pipeline  │     │
│   └──────────────────────────┘     │
│   ┌──────────────────────────┐     │
│   │   apps/backend/          │     │  ← FastAPI + WebSocket (Phase 9)
│   │   Event Router & API     │     │
│   └──────────────────────────┘     │
└────────────────┬───────────────────┘
                 │ Structured Events / WebSocket
                 ▼
┌────────────────────────────────────┐
│         LAPTOP 2                   │
│   Intel i5-1334U · Iris Xe         │
│                                    │
│   ┌──────────────────────────┐     │
│   │   apps/dashboard/        │     │  ← React Command Center (Phase 9)
│   │   Live Map + Alerts      │     │
│   └──────────────────────────┘     │
└────────────────────────────────────┘
```

---

## Repository Structure

```
ibvap/
│
├── apps/
│   ├── edge/           ← 🟢 Phases 1-8 — AI inference + event engine (Laptop 1 GPU)
│   │   ├── main.py     ← Single-camera entry point (pytorch or onnx backend)
│   │   └── multi_main.py ← Multi-camera entry point (Phase 8)
│   ├── backend/        ← ⏳ Phase 9 — FastAPI + WebSocket event broker
│   └── dashboard/      ← 🟢 Phase 9 — React command center (Laptop 2)
│
├── cv/                 ← Computer vision modules (no business logic)
│   ├── detection/      ← 🟢 DetectorBase + YOLODetector + ONNXDetector (Phase 7)
│   ├── tracking/       ← 🟢 Phase 2 — ByteTrack
│   ├── anpr/           ← 🟢 Phase 5 — Plate detection + OCR
│   ├── face/           ← ⏳ Phase 3+ — Face detection
│   └── preprocessing/  ← 🟢 Frame resize, ROI masking, CLAHE (Phase 6)
│
├── intelligence/       ← Event intelligence (geometry + rules, NOT neural nets)
│   ├── events/         ← 🟢 Phases 3+6 — Fence, loitering, crossing, night activity
│   ├── rules/          ← 🟢 Phase 4 — Rule evaluation engine
│   ├── risk/           ← 🟢 Phase 4+6 — Risk scoring (incl. NIGHT_MOVEMENT)
│   └── incidents/      ← 🟢 Phase 4 — Incident generation + correlation
│
├── pipelines/          ← 🟢 Phase 8 — Video pipeline backends
│   ├── base.py         ← VideoPipelineBase abstract class
│   ├── opencv/         ← 🟢 OpenCVPipeline (default, production-ready)
│   ├── gstreamer/      ← 🟢 GStreamerPipeline (hardware decode, fallback safe)
│   └── deepstream/     ← ⏳ Future — NVIDIA DeepStream multi-stream
│
├── models/
│   ├── pytorch/        ← .pt weight files (not committed to git)
│   ├── onnx/           ← 🟢 Phase 7 — ONNX models (run scripts/export_onnx.py)
│   └── tensorrt/       ← 🟢 Phase 7 — TRT engines (run scripts/export_tensorrt.py)
│
├── data/
│   └── videos/         ← Test video files (not committed to git)
│
├── datasets/           ← Training datasets (not committed to git)
├── benchmarks/         ← Benchmark scripts + results
├── configs/            ← YAML configs per phase/camera
├── scripts/            ← Utility scripts (download test video, etc.)
├── tests/              ← Unit + integration tests
├── docker/             ← ⏳ Phase 9 — Dockerfiles
├── docs/               ← Technical documentation
│
├── conftest.py         ← pytest root config
├── KNOWN_ISSUES.md     ← Bug tracker
├── README.md
└── pyproject.toml
```

> **Legend:** 🟢 Active · ⏳ Planned

---

## Hardware

| Machine | Role | Key Specs |
|---------|------|-----------|
| **Laptop 1** | AI Edge Node + Backend | Intel i5 13th Gen · 16 GB RAM · **RTX 4050 6 GB VRAM** |
| **Laptop 2** | Command Center Dashboard | Intel i5-1334U · 16 GB DDR4 · Intel Iris Xe |

---

## Current Phase: Phase 8 — Multi-Camera / GStreamer Pipeline

### Quick Start

#### 1. Activate the virtual environment

```powershell
# Windows PowerShell
.\.venv\Scripts\activate
```

#### 2. Get a test video

```bash
# Automatic download (free outdoor/street scene)
python scripts/get_test_video.py

# Or manually: copy any .mp4 to:
#   data/videos/test_video.mp4
```

#### 3. Run single-camera (Phase 5 baseline)

```bash
# Phase 5 — ANPR + Vehicle detection
python -m apps.edge.main --config configs/phase5_default.yaml

# Phase 6 — Night-mode + CLAHE low-light enhancement
python -m apps.edge.main --config configs/phase6_default.yaml

# Phase 7 — ONNX Runtime backend (export model first)
python scripts/export_onnx.py
python -m apps.edge.main --config configs/phase7_default.yaml

# Headless (no display window — SSH/remote)
python -m apps.edge.main --config configs/phase6_default.yaml --no-display
```

**Controls (display mode):** Press `q` or `Escape` to stop.

#### 4. Run multi-camera (Phase 8)

```bash
# Phase 8 — 2 cameras concurrently (headless by default)
python -m apps.edge.multi_main --config configs/phase8_default.yaml
```

#### 5. Run benchmarks

```bash
# Phase 1 — baseline resolution/FPS benchmark
python benchmarks/phase1_benchmark.py

# Phase 7 — PyTorch vs ONNX backend comparison
python scripts/export_onnx.py   # export model first
python benchmarks/phase7_benchmark.py

# Phase 8 — 1 vs 2 cameras concurrently
python benchmarks/phase8_benchmark.py
```

#### 6. Run Backend & Dashboard (Phase 9)

To run the full web application, you need to start both the FastAPI backend and the React frontend.

**Start the Backend (Terminal 1):**
```bash
.\.venv\Scripts\python -m uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000
```

**Start the Dashboard (Terminal 2):**
```bash
cd apps/dashboard
npm install
npm run dev
```

#### 7. Run tests

```bash
pytest tests/ -v
# Expected: 132 passed (Phases 1-8)
```

---

## Configuration & Camera Setup

Edit `configs/phase1_default.yaml` or use the **Dashboard UI (Camera Management)** to configure video sources. The platform supports multiple types of sources:

### 1. RTSP IP Cameras
The standard for CCTV cameras. You will need the camera's IP address, port (usually 554), username, password, and stream path.
* **Format:** `rtsp://<user>:<pass>@<ip>:<port>/<stream_path>`
* **Example:** `rtsp://admin:securepass123@192.168.1.50:554/cam/realmonitor?channel=1&subtype=0`

### 2. Local Video Files (Pre-recorded)
Useful for testing and benchmarking without a live camera.
* **Format:** Absolute or relative path to the `.mp4`, `.avi`, or `.mkv` file.
* **Example:** `data/videos/test_video.mp4`

### 3. USB Webcams
For testing directly from your laptop or connected USB cameras.
* **Format:** Integer index of the device (0 is usually the built-in webcam).
* **Example:** `0` (or `1`, `2`)

### 4. HTTP / MJPEG Streams
Often used by smartphone CCTV apps (like IP Webcam) or older IP cameras.
* **Format:** `http://<ip>:<port>/<stream_path>`
* **Example:** `http://192.168.1.100:8080/video`

```yaml
# Example YAML Configuration
camera:
  source: "rtsp://admin:pass@192.168.1.50:554/stream"
  name: "BOP-CAM-01"

detector:
  model: "models/pytorch/yolov8n.pt"
  device: "cuda:0"
  conf_threshold: 0.40
  imgsz: 640
  inference_every_n_frames: 3
```

---

## Development Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 0** | ✅ Done | Hardware Benchmark — CUDA, PyTorch, FPS/VRAM baseline |
| **Phase 1** | ✅ Done | Single Camera Detection |
| **Phase 2** | ✅ Done | Multi-Object Tracking (ByteTrack + trajectory history) |
| **Phase 3** | ✅ Done | Event Engine (Virtual Fence, Loitering, Line Crossing) |
| **Phase 4** | ✅ Done | Risk + Incident Intelligence |
| **Phase 5** | ✅ Done | Vehicle Intelligence + ANPR |
| **Phase 6** | ✅ Done | Night-time Performance (CLAHE + NightActivityEngine) |
| **Phase 7** | ✅ Done | ONNX Optimization (ONNXDetector + benchmark scripts) |
| **Phase 8** | ✅ Done | Multi-Camera + GStreamer Pipeline Abstraction Layer |
| **Phase 9** | 🟢 Active | Backend API + React Command Center |
| Phase 10 | ⏳ | Hardening + Bug Testing |
| Phase 11 | ⏳ | SIH Competition Demo Build |

---

## Golden Rules

1. **Measure before optimizing** — no guessing.
2. **Geometry > AI** — don't use a neural net where a line equation works.
3. **Detection ≠ Incident** — one frame does not make an alert.
4. **Don't process every frame** — skip if it adds no value.
5. **Drop stale frames** — current > historical.
6. **False positives kill demos** — filter aggressively.
7. **Simple pipeline first** — one camera, one detector, one fence, one alert.
8. **Every feature must earn its place** — does it improve the border demo?
9. **Benchmark sustained, not peak** — test for 30–60 min, not 30 seconds.
10. **Feature freeze before competition** — no last-minute architecture changes.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `ultralytics` | YOLO detection |
| `opencv-python` | Video capture, annotation, display |
| `numpy` | Array operations |
| `pyyaml` | Config loading |
| `nvidia-ml-py` | GPU metrics (VRAM, utilization, temp) |
| `psutil` | CPU/RAM metrics |
| `supervision` | Visualization utilities (prototype phase) |

---

## Related

- [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) — Bug tracker
- [`context.md`](context.md) — Full project context and strategic decisions
- [`apps/edge/README.md`](apps/edge/README.md) — Edge AI node details
- [`apps/backend/README.md`](apps/backend/README.md) — Backend API design (Phase 9)
- [`apps/dashboard/README.md`](apps/dashboard/README.md) — Dashboard design (Phase 9)
- [`benchmarks/`](benchmarks/) — Benchmark scripts and results
- [`configs/`](configs/) — YAML configuration files
- [`Test videos`](https://drive.google.com/drive/folders/1gUPrg_Vshhn-fADPCzQ0ptClaKeLrFjz?usp=sharing) — Test videos

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
│   ├── edge/           ← 🟢 Phases 1-3 ACTIVE — AI inference + event engine (Laptop 1 GPU)
│   ├── backend/        ← ⏳ Phase 9 — FastAPI + WebSocket event broker
│   └── dashboard/      ← ⏳ Phase 9 — React command center (Laptop 2)
│
├── cv/                 ← Computer vision modules (no business logic)
│   ├── detection/      ← DetectorBase + YOLODetector
│   ├── tracking/       ← ⏳ Phase 2 — ByteTrack / BoT-SORT
│   ├── anpr/           ← ⏳ Phase 5 — Plate detection + OCR
│   ├── face/           ← ⏳ Phase 3+ — Face detection
│   └── preprocessing/  ← Frame resize, ROI masking
│
├── intelligence/       ← Event intelligence (geometry + rules, NOT neural nets)
│   ├── events/         ← 🟢 Phase 3 — Virtual fence, loitering, line crossing
│   ├── rules/          ← ⏳ Phase 4 — Rule evaluation engine
│   ├── risk/           ← ⏳ Phase 4 — Risk scoring
│   └── incidents/      ← ⏳ Phase 4 — Incident generation + correlation
│
├── pipelines/          ← Video pipeline backends
│   ├── opencv/         ← ⏳ Current Python prototype
│   ├── gstreamer/      ← ⏳ Phase 8 — Hardware decode
│   └── deepstream/     ← ⏳ Phase 8 — NVIDIA DeepStream multi-stream
│
├── models/
│   ├── pytorch/        ← .pt weight files (not committed to git)
│   ├── onnx/           ← ⏳ Phase 7 — exported ONNX models
│   └── tensorrt/       ← ⏳ Phase 7 — compiled TRT engines
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

## Current Phase: Phase 3 — Event Intelligence Engine

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

#### 3. Run the edge processor

```bash
python -m apps.edge.main --config configs/phase3_default.yaml

# Headless (no display window — SSH/remote)
python -m apps.edge.main --config configs/phase3_default.yaml --no-display

# Phase 2 only (tracking, no event engine zones)
python -m apps.edge.main --config configs/phase2_default.yaml

# Phase 1 only (detection only, no tracking)
python -m apps.edge.main --config configs/phase1_default.yaml
```

**Controls (display mode):** Press `q` or `Escape` to stop.

#### 4. Run the hardware benchmark

```bash
# Quick: yolov8n, all 5 resolutions, 500 frames each
python benchmarks/phase1_benchmark.py

# Thermal soak (30 min per config)
python benchmarks/phase1_benchmark.py --model models/pytorch/yolov8n.pt --duration 1800

# Compare nano vs small
python benchmarks/phase1_benchmark.py \
    --model models/pytorch/yolov8n.pt models/pytorch/yolov8s.pt
```

#### 5. Run tests

```bash
pytest tests/ -v
```

---

## Configuration

Edit `configs/phase1_default.yaml`:

```yaml
camera:
  source: "data/videos/test_video.mp4"   # or rtsp://...

detector:
  model: "models/pytorch/yolov8n.pt"
  device: "cuda:0"                        # RTX 4050
  conf_threshold: 0.40
  imgsz: 640
  inference_every_n_frames: 3             # Effective ~10 FPS inference
```

---

## Development Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 0** | ✅ Done | Hardware Benchmark — CUDA, PyTorch, FPS/VRAM baseline |
| **Phase 1** | ✅ Done | Single Camera Detection |
| **Phase 2** | ✅ Done | Multi-Object Tracking (ByteTrack + trajectory history) |
| **Phase 3** | 🔧 In Progress | Event Engine (Virtual Fence, Loitering, Line Crossing) |
| Phase 4 | ⏳ | Risk + Incident Intelligence |
| Phase 5 | ⏳ | Vehicle Intelligence + ANPR |
| Phase 6 | ⏳ | Night-time Performance |
| Phase 7 | ⏳ | TensorRT / ONNX Optimization |
| Phase 8 | ⏳ | DeepStream / GStreamer Migration |
| Phase 9 | ⏳ | Backend API + React Command Center |
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

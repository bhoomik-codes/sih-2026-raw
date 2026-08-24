# IBVAP — Intelligent Border Video Analytics Platform

**SIH 2026 · Problem Statement SIH26187**  
**Organization:** Ministry of Home Affairs / Sashastra Seema Bal

> Transform existing IP-based CCTV infrastructure into an AI-powered border surveillance platform — without expensive dedicated hardware.

---

## Architecture Overview

```
CCTV Camera (RTSP)
      ↓
 Laptop 1 — AI Edge Node (RTX 4050)
      ↓  [WebSocket / Events]
 Laptop 2 — Command Center Dashboard
```

### Pipeline

```
Raw Video → Detection → Tracking → Event Engine → Risk Engine → Incident → Alert
```

---

## Repository Structure

```
ibvap/
├── apps/
│   ├── edge/           ← Phase 1: Detection loop (Laptop 1)
│   ├── backend/        ← Phase 9: FastAPI + WebSocket server
│   └── dashboard/      ← Phase 9: React command center (Laptop 2)
├── cv/
│   ├── detection/      ← Detector abstraction (DetectorBase, YOLODetector)
│   ├── tracking/       ← Phase 2: ByteTrack / BoT-SORT
│   ├── anpr/           ← Phase 5: Plate detection + OCR
│   └── preprocessing/  ← Frame resize, ROI masking
├── intelligence/
│   ├── events/         ← Phase 3: Virtual fence, loitering, line crossing
│   ├── rules/          ← Phase 3: Rule evaluation engine
│   ├── risk/           ← Phase 4: Risk scoring
│   └── incidents/      ← Phase 4: Incident generation
├── pipelines/          ← Phase 8: GStreamer / DeepStream
├── models/             ← Model weights (not committed to git)
├── benchmarks/         ← Benchmark scripts + results
├── configs/            ← YAML configs per phase / camera
├── tests/              ← Unit + integration tests
├── docs/
├── KNOWN_ISSUES.md
└── pyproject.toml
```

---

## Hardware

| Machine | Role | Specs |
|---------|------|-------|
| **Laptop 1** | AI Edge Processing Node | Intel i5 13th Gen · 16 GB RAM · **RTX 4050 6 GB VRAM** |
| **Laptop 2** | Command Center Dashboard | Intel i5-1334U · 16 GB DDR4 · Intel Iris Xe |

---

## Current Phase: Phase 1 — Single Camera Detection

### Goals
- Stable human and vehicle detection from a single video source
- No memory leaks, no crashes, stable FPS over 30–60 minutes
- Benchmark table: FPS / VRAM / latency across models and resolutions

### Quick Start

#### 1. Install dependencies

```bash
# Create virtual environment (recommended)
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# Install project
pip install -e ".[dev]"
```

#### 2. Run the edge processor

```bash
# With a local test video
python -m apps.edge.main --config configs/phase1_default.yaml

# Override source
python -m apps.edge.main --config configs/phase1_default.yaml --source rtsp://192.168.1.10:554/stream

# Headless (no display window)
python -m apps.edge.main --config configs/phase1_default.yaml --no-display
```

**Controls (display mode):** Press `q` or `Escape` to stop.

#### 3. Run the benchmark

```bash
# Quick benchmark — yolov8n, all resolutions, 500 frames each
python benchmarks/phase1_benchmark.py

# Multiple models
python benchmarks/phase1_benchmark.py --model yolov8n.pt yolov8s.pt

# Thermal soak test (30 minutes per config)
python benchmarks/phase1_benchmark.py --model yolov8n.pt --duration 1800

# Specific resolutions
python benchmarks/phase1_benchmark.py --resolutions 640x640 1280x720
```

#### 4. Run tests

```bash
pytest tests/ -v
```

---

## Configuration

Edit `configs/phase1_default.yaml`:

```yaml
camera:
  source: "test_video.mp4"   # or rtsp://...
  max_queue_size: 2          # Keep small — latest-frame strategy

detector:
  model: "yolov8n.pt"        # yolov8n / yolov8s / yolov8m
  device: "cuda:0"           # RTX 4050
  conf_threshold: 0.40
  imgsz: 640
  inference_every_n_frames: 3
```

---

## Development Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 0** | ✅ Hardware Benchmark | RTX 4050 baseline — CUDA, PyTorch, FPS/VRAM |
| **Phase 1** | 🔧 In Progress | Single Camera Detection |
| Phase 2 | — | Multi-Object Tracking (ByteTrack / BoT-SORT) |
| Phase 3 | — | Event Engine (Virtual Fence, Loitering, Line Crossing) |
| Phase 4 | — | Risk + Incident Intelligence |
| Phase 5 | — | Vehicle Intelligence + ANPR |
| Phase 6 | — | Night-time Performance |
| Phase 7 | — | TensorRT / ONNX Optimization |
| Phase 8 | — | DeepStream / GStreamer Migration |
| Phase 9 | — | Command Center (React + WebSocket + Leaflet) |
| Phase 10 | — | Hardening + Bug Testing |
| Phase 11 | — | SIH Competition Demo Build |

---

## Golden Rules

1. Do not optimize before measuring.
2. Do not add AI where geometry and rules are sufficient.
3. Detection is not an incident.
4. Do not process every frame if it provides no additional value.
5. Current frames are more valuable than a queue of stale frames.
6. False positives can damage the prototype more than lower detection accuracy.
7. Build the simplest possible working pipeline first.
8. Every feature must answer: _Does this improve the border surveillance demo?_
9. Benchmark sustained performance, not 30-second peak performance.
10. Before the competition: **FEATURE FREEZE**.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `ultralytics` | YOLO detection (Phase 1) |
| `opencv-python` | Video capture, annotation, display |
| `numpy` | Array operations |
| `pyyaml` | Config loading |
| `pynvml` | GPU metrics (VRAM, utilization, temp) |
| `psutil` | CPU/RAM metrics |
| `supervision` | Visualization utilities (prototype phase) |

---

## Related Documentation

- [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) — Bug tracker
- [`context.md`](context.md) — Full project context and strategic decisions
- [`benchmarks/`](benchmarks/) — Benchmark scripts and results
- [`configs/`](configs/) — YAML configuration files

# IBVAP — Intelligent Border Video Analytics Platform (v2.0)

**SIH 2026 · Problem Statement SIH26187**  
**Organization:** Ministry of Home Affairs / Sashastra Seema Bal (SSB)

> **Transforming existing CCTV infrastructure into a real-time, AI-driven border surveillance & threat intelligence platform.**

---

## 📑 Table of Contents
- [Executive Overview](#-executive-overview)
- [System Architecture](#-system-architecture)
- [Key Features & Capabilities](#-key-features--capabilities)
- [Repository Structure](#-repository-structure)
- [Quick Start Guide](#-quick-start-guide)
- [Running Full Demo](#-running-full-demo)
- [Video Feeds & Camera Ingestion](#-video-feeds--camera-ingestion)
- [Threat Intelligence & Risk Engine](#-threat-intelligence--risk-engine)
- [Command Center Dashboard](#-command-center-dashboard)
- [Benchmarks & Performance](#-benchmarks--performance)
- [Verification & Testing](#-verification--testing)
- [Engineering Principles](#-engineering-principles)

---

## 🛡️ Executive Overview

IBVAP is a lightweight, edge-deployable multi-camera surveillance platform designed specifically for border security and perimeter protection. It converts commodity IP cameras, RTSP streams, USB webcams, and drone feeds into intelligent monitoring nodes that:
1. **Detect & Track** intruders and vehicles in challenging conditions (night-time, low light, rain).
2. **Compute Real-Time Spatial Events** (Virtual Fence Crossing, Zero-Line Breach, Loitering, Forbidden Direction).
3. **Perform Automatic Number Plate Recognition (ANPR)** against watchlists without stalling video pipelines.
4. **Aggregate Threats into Cumulative Risk Scores** to prevent alert fatigue and eliminate false positives.
5. **Stream Real-Time Tactical Feeds & Alerts** to a web-based military-grade Command Center UI.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SURVEILLANCE SOURCES                             │
│   RTSP IP Cameras · Video Files (.mp4) · USB Webcams · Drone Feeds      │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                 H.264 / MJPEG / RTSP Stream Ingestion
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              EDGE AI INFERENCE NODE (Laptop 1 / Edge Box)               │
│                                                                         │
│  ┌───────────────────────┐      ┌──────────────────────────────────┐   │
│  │   Video Pipeline      │      │     Computer Vision Pipeline     │   │
│  │  - OpenCV / GStreamer │ ───► │  - YOLOv8 (PyTorch / ONNX / TRT) │   │
│  │  - Ring Buffer Queue  │      │  - ByteTrack (Multi-Object)      │   │
│  │  - Hardware Watchdog  │      │  - ANPR & Plate OCR Pipeline     │   │
│  └───────────────────────┘      └─────────────────┬────────────────┘   │
│                                                   │ Detections          │
│                                                   ▼                     │
│  ┌───────────────────────┐      ┌──────────────────────────────────┐   │
│  │  Local MJPEG Streamer │      │    Intelligence & Risk Engine    │   │
│  │  - Port 8081+ HTTP    │      │  - Virtual Fence & Line Crossing │   │
│  │  - Live Annotated HUD │      │  - Loitering & Night Detection   │   │
│  └───────────────────────┘      │  - Dynamic Multi-Event Scorer    │   │
│                                 └─────────────────┬────────────────┘   │
│                                                   │ Incidents / Alerts  │
│                                                   ▼                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │   Non-Blocking WebSocket Transmitter (ws://localhost:8000/ws)   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                 Telemetry / Incidents / Camera Status
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CENTRAL BACKEND (FastAPI)                          │
│                                                                         │
│  - WebSocket Event Multiplexer & Broadcast Broker                       │
│  - Camera Stream Reverse Proxy (`/api/streams/{camera_id}`)             │
│  - Supabase / PostgreSQL Event & Incident Persistence Engine            │
│  - Evidence & Video File Storage (`/api/videos`)                        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                 REST API & Real-Time WebSocket Push
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               COMMAND CENTER DASHBOARD (Laptop 2 / Web)                 │
│               React 18 · TypeScript · Vite · TailwindCSS                │
│                                                                         │
│  ┌───────────────────────┐      ┌──────────────────────────────────┐   │
│  │ Multi-Camera Matrix   │      │ Tactical Incident Center         │   │
│  │ - Live MJPEG Streams  │      │ - Dynamic Risk Gauges (0-100)    │   │
│  │ - AI Detection BBoxes │      │ - Real-Time Alert Push Toasts    │   │
│  │ - HUD Diagnostics     │      │ - Forensic Event Timelines       │   │
│  └───────────────────────┘      └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🌟 Key Features & Capabilities

* **Multi-Backend AI Engine:** Supports standard PyTorch weights (`.pt`), accelerated **ONNX Runtime**, and **NVIDIA TensorRT** with unified detection abstractions.
* **ByteTrack Multi-Object Tracking:** Assigns persistent IDs, handles temporary occlusions, and automatically cleans up stale tracks to prevent memory leaks.
* **Intelligent Geometric Threat Analysis:**
  * **Virtual Fence Breaches:** Polygon containment checks with custom class filtering.
  * **Line Crossing Directionality:** Ray intersection vectors detecting intrusion vs. egress.
  * **Loitering Detection:** Time-in-zone thresholds with tracking history.
  * **Night-Time Infiltration:** Automatic solar/time-aware sensitivity boosting and CLAHE low-light enhancement.
* **Smart ANPR Pipeline:** Buffers crops per tracked vehicle and executes OCR on the highest-resolution frame to preserve GPU compute.
* **Dynamic Threat Escalation:** Translates raw detections into unified **Security Incidents** with calculated threat levels:
  * `LOW` (0–29) · `MEDIUM` (30–59) · `HIGH` (60–79) · `CRITICAL` (80–100).
* **Zero-Latency Video Streaming:** Independent background HTTP MJPEG streaming (`/stream`) with real-time HUD annotations.
* **Dual-Laptop Deployment:** Laptop 1 handles GPU Edge compute + FastAPI backend; Laptop 2 runs the tactical React Command Center over LAN.

---

## 📂 Repository Structure

```
ibvap/
├── apps/
│   ├── edge/               # Edge processing node (Camera ingest, YOLO, ByteTrack, ANPR, Events, Streamer)
│   │   ├── main.py         # Single-camera Edge node CLI
│   │   ├── multi_main.py   # Multi-camera concurrent Edge supervisor
│   │   ├── processor.py    # Core frame inference and intelligence loop
│   │   ├── streamer.py     # High-throughput MJPEG HTTP video server
│   │   └── transmitter.py  # Non-blocking WebSocket client to backend
│   │
│   ├── backend/            # FastAPI Command Center server
│   │   ├── main.py         # REST endpoints, WebSocket broker, stream proxies
│   │   └── db.py           # Supabase & PostgreSQL persistence adapter
│   │
│   └── dashboard/          # React + Vite + TypeScript Command Center
│       ├── src/pages/      # Command Center, Camera Management, Incidents, Map, Health
│       ├── src/components/ # LiveStream HUD, IncidentDetailModal, AlertToast, CameraGrid
│       └── src/websocket/  # Resilient auto-reconnecting WebSocket client
│
├── cv/                     # Pure Computer Vision algorithms
│   ├── detection/          # YOLODetector, ONNXDetector, DetectorBase
│   ├── tracking/           # ByteTracker, Kalman filter, trajectory management
│   ├── anpr/               # Plate preprocessor (CLAHE, bilateral filter) & PlateOCR
│   ├── face/               # Face detector & feature extractor
│   └── preprocessing/      # Low-light contrast enhancement & frame resizing
│
├── intelligence/           # Threat Rules & Incident Scoring
│   ├── events/             # Virtual Fence, Line Crossing, Loitering, Night Activity
│   ├── risk/               # Dynamic threat accumulator & weight matrix
│   └── incidents/          # Incident generator & multi-event correlation
│
├── pipelines/              # Video ingestion pipeline backends
│   ├── opencv/             # OpenCVPipeline with non-blocking watchdog
│   └── gstreamer/          # GStreamerPipeline with hardware acceleration
│
├── configs/                # Ready-to-run YAML configurations for all operational phases
├── scripts/                # Utility scripts (get test videos, export ONNX, test pipelines)
├── benchmarks/             # Benchmarks (FPS, latency, VRAM, single vs multi-camera)
└── tests/                  # Pytest test suite (132 passed tests)
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites & Environment Setup

Ensure you have **Python 3.11+** and **Node.js 18+** installed.

```bash
# Clone the repository
git clone https://github.com/bhoomik-codes/sih-2026-raw.git
cd sih-2026-raw

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate        # On Windows: .\.venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### 2. Download Test Surveillance Footage

```bash
# Automatically downloads sample surveillance video into data/videos/test_video.mp4
python scripts/get_test_video.py
```

---

## 🚀 Running Full Demo

Running the entire IBVAP platform involves three simple steps across terminals:

```
Terminal 1: Central Backend  ───►  Terminal 2: React Dashboard  ───►  Terminal 3: Edge AI Node
(Port 8000)                        (Port 5173)                         (Video Stream Port 8081)
```

### Terminal 1: Start the Backend (FastAPI + WebSocket Server)
```bash
source .venv/bin/activate
uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Start the Command Center Dashboard
```bash
cd apps/dashboard
npm install
npm run dev
```
*Open [http://localhost:5173](http://localhost:5173) in your browser.*

### Terminal 3: Start Edge AI Processing with Live Video Streaming
```bash
source .venv/bin/activate

# Run Edge AI with live streaming enabled on port 8081
python -m apps.edge.main \
  --config configs/phase1_default.yaml \
  --source data/videos/border_crossing_test.mp4 \
  --stream-port 8081
```

> **Tip:** You can also add and start cameras directly through the **Camera Management** page in the Web Dashboard!

---

## 📹 Video Feeds & Camera Ingestion

IBVAP natively supports four primary video source types:

| Source Type | Configuration Format | Example |
| :--- | :--- | :--- |
| **RTSP IP Camera** | `rtsp://<user>:<pass>@<ip>:<port>/<stream>` | `rtsp://admin:pass123@192.168.1.50:554/h264` |
| **Local Video File** | Absolute or relative path to `.mp4` / `.avi` | `data/videos/border_crossing_test.mp4` |
| **USB / Integrated Webcam** | Device integer index | `0` or `1` |
| **HTTP / Smartphone Stream** | HTTP URL with MJPEG stream | `http://192.168.1.100:8080/video` |

### Multi-Camera Concurrent Processing (Phase 8)
To run multi-camera concurrent surveillance on a single node:
```bash
python -m apps.edge.multi_main --config configs/phase8_default.yaml
```

---

## 🧠 Threat Intelligence & Risk Engine

IBVAP decouples raw AI inference from strategic threat scoring. A single frame detection does not trigger an alarm; alarms require spatial and temporal risk accumulation.

```
Individual Detections (YOLO + ByteTrack)
               │
               ▼
   Spatial & Rule Evaluation
   ├── Zone Intrusion     (+30 pts)
   ├── Perimeter Crossing (+40 pts)
   ├── Loitering > 5s     (+25 pts)
   ├── Watchlist ANPR     (+60 pts)
   └── Night Movement     (+25 pts)
               │
               ▼
   Cumulative Risk Score Scored (0 - 100)
   ├── Score >= 80 ──► CRITICAL INCIDENT (Immediate Tactical Alert)
   ├── Score >= 60 ──► HIGH SEVERITY
   ├── Score >= 30 ──► MEDIUM SEVERITY
   └── Score < 30  ──► INFORMATIONAL / LOW
```

---

## 🖥️ Command Center Dashboard

The React tactical dashboard is designed with a high-contrast dark aesthetic for military command centers:

1. **Command Center (Main):** Live multi-camera grid, annotated MJPEG player, instant toast notifications, active alerts breakdown, and event stream timeline.
2. **Camera Management:** Add, configure, start, and stop IP, USB, or MP4 surveillance feeds on the fly.
3. **Incident Center:** Searchable catalog of security breaches with detailed forensic explanations and incident acknowledge workflows.
4. **Explainability Modal:** Real-time risk gauge, contributing threat breakdown, camera metadata, and full event audit trail.
5. **System Health:** CPU, GPU, VRAM, and FPS telemetry across all connected Edge nodes.

---

## 📊 Benchmarks & Performance

IBVAP includes automated benchmarking utilities to validate sustained hardware performance:

```bash
# Run baseline single-camera pipeline benchmark
python benchmarks/phase1_benchmark.py

# Export YOLOv8 to ONNX format
python scripts/export_onnx.py

# Run PyTorch vs. ONNX Runtime inference benchmark
python benchmarks/phase7_benchmark.py

# Run Multi-Camera throughput benchmark (1 vs. 2 cameras)
python benchmarks/phase8_benchmark.py
```

### Verified Hardware Targets
* **Laptop 1 (Inference + Backend):** Intel i5 13th Gen · 16 GB RAM · NVIDIA RTX 4050 (6 GB VRAM) — *Target: 30+ FPS sustained*.
* **Laptop 2 (Command Center):** Intel i5-1334U · 16 GB RAM · Intel Iris Xe Graphics.

---

## 🧪 Verification & Testing

The repository maintains an automated test suite with full coverage across video ingestion, detectors, tracking, event rules, risk scoring, and incident generation.

```bash
# Run all unit and integration tests
.venv/bin/pytest tests/ -v
# Output: 132 passed in ~7s

# Check and validate code quality
.venv/bin/ruff check .
```

---

## 🎯 Engineering Principles

1. **Measure before optimizing:** Every optimization must be benchmarked on sustained runs, not short bursts.
2. **Geometry over Neural Nets:** Use analytical geometry (raycasting, polygons) for spatial rules rather than heavy neural classifiers.
3. **Detection ≠ Incident:** Multi-event correlation prevents false positives and alarm fatigue.
4. **Drop stale frames:** In live security, the current frame is infinitely more valuable than a delayed backlog frame.
5. **Non-blocking Pipelines:** AI inference and telemetry transmission must never block the camera ingestion loop.

---

## 👥 Team & Documentation Links

- [Developer & Architecture Guide](docs/DEVELOPER_GUIDE.md)
- [Known Issues Tracker](KNOWN_ISSUES.md)
- [Database Schema & Design](schema.md)
- [Development Roadmap & Tasks](tasks.md)
- [Edge Processing Node Documentation](apps/edge/README.md)
- [Backend API Documentation](apps/backend/README.md)
- [Command Center Dashboard Documentation](apps/dashboard/README.md)

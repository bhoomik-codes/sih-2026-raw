# IBVAP — Intelligent Border Video Analytics Platform (v2.0)

**SIH 2026 · Problem Statement SIH26187**  
**Organization:** Ministry of Home Affairs / Sashastra Seema Bal (SSB)

> **Transforming existing CCTV infrastructure into a real-time, AI-driven border surveillance & threat intelligence platform.**

---

## 📑 Table of Contents
- [Executive Overview](#-executive-overview)
- [Complete Feature List](#-complete-feature-list)
- [Complete Tech Stack](#-complete-tech-stack)
- [System Architecture & Workflow](#-system-architecture--workflow)
- [Setup & Execution Instructions](#-setup--execution-instructions)
- [Development Journey: Challenges & Solutions](#-development-journey-challenges--solutions)

---

## 🛡️ Executive Overview

IBVAP is a lightweight, edge-deployable multi-camera surveillance platform designed specifically for border security and perimeter protection. It converts commodity IP cameras, RTSP streams, USB webcams, and drone feeds into intelligent monitoring nodes. By coupling Computer Vision with geometric spatial logic, IBVAP translates raw pixels into cumulative tactical risk scores, virtually eliminating false positives and alert fatigue for border operators.

---

## 🌟 Complete Feature List

1. **Multi-Backend AI Engine:** Hardware-accelerated object detection using YOLOv8, supporting raw PyTorch (`.pt`), ONNX Runtime, and NVIDIA TensorRT.
2. **Persistent Multi-Object Tracking:** ByteTrack integration assigning persistent vehicle/person IDs, handling occlusions, and utilizing garbage collection for stale tracks to prevent memory leaks over long deployments.
3. **Geometric Threat Analysis (Event Engine):**
   - **Virtual Fence Breaches:** Polygon containment algorithms filtering specific classes (e.g., detecting humans but ignoring dogs).
   - **Line Crossing:** Directional vector intersection detecting intrusion vs. authorized egress.
   - **Loitering Detection:** Time-in-zone thresholds paired with trajectory tracking.
   - **Night-Time Infiltration:** Automatic solar-aware sensitivity boosting.
4. **Smart Automatic Number Plate Recognition (ANPR):** Pre-processes vehicle crops (CLAHE, Bilateral filtering, deskewing) and executes OCR (via EasyOCR) without stalling the primary video pipeline.
5. **Dynamic Threat Escalation:** Accumulates raw spatial events into unified **Security Incidents** with threat levels ranging from 0 (Informational) to 100 (Critical/Immediate Action).
6. **Zero-Latency Tactical Video Streaming:** High-throughput background HTTP MJPEG streaming with real-time HUD annotations, independent of the inference thread.
7. **Enterprise Observability & Audit Trails:** Real-time persistence of Edge node hardware telemetry (CPU, RAM, GPU utilization) and human operator actions via PostgreSQL and Supabase.
8. **Military-Grade Command Center:** React-based tactical dashboard featuring Leaflet live-maps, dynamic risk gauges, push-toast alerts, and forensic timeline queries.

---

## 💻 Complete Tech Stack

**Edge AI Node (Compute & Vision):**
- Python 3.11+
- OpenCV (Video Ingestion & Geometric Drawing)
- PyTorch / ONNX Runtime (Neural Network Inference)
- Ultralytics (YOLOv8 Weights)
- ByteTrack (Multi-Object Tracking)
- EasyOCR (ANPR Pipeline)
- `psutil` & `pynvml` (Hardware Telemetry)

**Command Center Backend (Routing & Persistence):**
- FastAPI & Uvicorn (REST API)
- WebSockets (Real-time Full-Duplex Broker)
- Supabase / PostgreSQL (Time-series Events, Incidents, & Metrics)

**Command Center Dashboard (Tactical UI):**
- React 18 & TypeScript
- Vite
- TailwindCSS (Styling & Dark Mode)
- Leaflet (Live Map & GPS Marker Plotting)
- Recharts (Hardware Telemetry Visualizations)

---

## 🏗️ System Architecture & Workflow

The actual implemented workflow distributes compute across Edge and Command nodes.

1. **Video Ingestion:** The Edge Node ingests video from an RTSP IP Camera, USB webcam, or local MP4 file. The ingestion runs in a dedicated thread on a non-blocking bounded queue to ensure real-time latency.
2. **AI Inference & Tracking:** Every $N$ frames, the video frame is pre-processed and passed through the YOLO detector. Detected bounding boxes are fed to ByteTrack, appending historical trajectories to unique object IDs.
3. **Intelligence Evaluation:** The Event Engine uses raycasting and polygon intersection math to check if tracked objects violated spatial rules (Virtual Fence, Line Cross, Loitering). Vehicle crops are sent to the ANPR engine.
4. **Incident Escalation:** Raw events are fed into the Risk Scorer. If an object accumulates enough points (e.g. `Loitering (25)` + `Fence Breach (30)` = `Medium Incident (55)`), an **Incident** is generated.
5. **Telemetry & Broadcast:** The Edge Node annotates the frame (HUD), streams it via an MJPEG HTTP server, and uses a non-blocking WebSocket transmitter to push Events, Incidents, and Hardware Metrics to the Backend.
6. **Backend Persistence:** The FastAPI Backend receives the WebSocket JSON payload and immediately upserts it to Supabase (PostgreSQL) tables (`events`, `incidents`, `system_metrics`, `audit_logs`). 
7. **Tactical UI:** The React Dashboard, connected to the same backend via WebSocket, instantly reflects the new threat on the map, updates the Risk Gauge, triggers a red toast alert, and graphs the incoming edge GPU telemetry.

---

## ⚡ Setup & Execution Instructions

IBVAP is designed to be deployed across two separate machines over a Local Area Network (LAN).

### Step 1: Clone & Install (Both Laptops)
On both laptops, ensure Python 3.11+ and Node.js 18+ are installed.
```bash
git clone https://github.com/bhoomik-codes/sih-2026-raw.git
cd sih-2026-raw
python3 -m venv .venv
# Windows: .\.venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -e ".[dev]"
```

### Step 2: Configure Database Credentials (Laptop 2)
In the project root of Laptop 2, create a `.env` file (copy from `.env.example`) and fill in your Supabase credentials:
```env
DATABASE_ENABLED=true
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
```

### Step 3: Run the Command Center Backend & Dashboard (Laptop 2)
**Terminal A (Backend):**
```bash
uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000 --reload
```
**Terminal B (Dashboard):**
```bash
cd apps/dashboard
npm install
npm run dev -- --host
```
*Take note of Laptop 2's IPv4 address on the LAN (e.g., `192.168.1.100`).*

### Step 3: Run the System (All-In-One Launcher)
To start both the Command Center Backend and Dashboard simultaneously, run the unified launcher:

```bash
.\1_Run_All_In_One.bat
```

This will automatically:
1. Start the FastAPI Backend on `http://localhost:8001`
2. Start the React Dashboard on `http://localhost:5173`

*Once the Dashboard opens in your browser, you can dynamically add, start, and manage Edge Cameras directly from the "Camera Management" UI! The backend will autonomously spawn and manage the edge AI processes.*

---

## 🚧 Development Journey: Challenges & Solutions

Building a robust, real-time computer vision system introduced severe multi-threading and memory constraints. Below are the major challenges we faced and how we engineered our way around them (documented in `KNOWN_ISSUES.md`).

### 1. The OpenCV RTSP Blocking Hang
**Challenge:** If an RTSP stream (IP camera) silently dropped from the network, `cv2.VideoCapture.read()` would block indefinitely instead of returning `False`, completely freezing the Edge Node and preventing reconnection logic.
**Solution:** We moved video ingestion to a dedicated `threading.Thread` and implemented an **Active Watchdog Monitor**. The watchdog tracks the timestamp of the last successful read. If the delta exceeds a timeout (e.g., 5 seconds), the watchdog forces a `cap.release()` and auto-reconnects, ensuring the AI loop never stalls.

### 2. Unbounded Memory Leaks in ByteTrack
**Challenge:** The ByteTracker maintained a dictionary of object trajectories. During long deployments, when objects left the frame, their tracks were "temporarily suspended" for occlusion handling, but never permanently deleted. Over hours, this caused severe RAM/VRAM bloat and eventual Out-Of-Memory (OOM) crashes.
**Solution:** We implemented a TTL (Time-To-Live) garbage collector (`_track_last_seen`). Any track ID unseen for `max(60, track_buffer * 2)` frames is now aggressively purged from the trajectory dictionary, stabilizing memory at a constant footprint.

### 3. Sequential Queue Starvation in Multi-Camera
**Challenge:** When running 4 cameras on a single node, the manager looped over their queues using a blocking timeout (`queue.get(timeout=0.05)`). If all queues were empty, it blocked sequentially for a total of `0.20s`, throttling the pipeline to a maximum of 5 FPS regardless of GPU power.
**Solution:** We rewrote `MultiCameraManager` to use non-blocking `get_nowait()` polling, spreading a single global timeout across all cameras simultaneously.

### 4. Frame Stream Bypass (Display vs Stream)
**Challenge:** When running with a local OpenCV display window (`cv2.imshow`), the HTTP MJPEG streamer received zero frames due to an exclusive `if/elif` branch in the rendering logic.
**Solution:** We decoupled the local window renderer from the MJPEG HTTP encoder, passing copies of the annotated frame to both systems so operators could view the feed locally on the edge node and remotely in the dashboard concurrently.

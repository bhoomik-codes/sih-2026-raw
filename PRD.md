# IBVAP — Product Requirements Document

**Product:** Intelligent Border Video Analytics Platform (IBVAP)
**Problem Statement:** SIH26187 — AI-Based Intelligent Video Analytics Platform for Border Surveillance using Existing CCTV Infrastructure
**Organization:** Ministry of Home Affairs / Sashastra Seema Bal (SSB)
**Document Version:** 2.0 (Clean Structured PRD)

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [System Architecture](#2-system-architecture)
3. [Functional Requirements](#3-functional-requirements)
4. [Dashboard (GUI) Requirements](#4-dashboard-gui-requirements)
5. [GUI Locations & Behavior](#5-gui-locations--behavior)
6. [Smartphone as CCTV Camera](#6-smartphone-as-cctv-camera)
7. [Miniature Smartphone Dashboard (LAN)](#7-miniature-smartphone-dashboard-lan)
8. [Backend & API Requirements](#8-backend--api-requirements)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Out of Scope (Initial)](#10-out-of-scope-initial)
11. [MVP Definition](#11-mvp-definition)
12. [Development Phases](#12-development-phases)

---

# 1. Product Overview

## 1.1 Vision

Transform existing IP-based CCTV infrastructure into an AI-powered border surveillance platform **without expensive dedicated hardware**. Existing cameras become intelligent sensors through software.

## 1.2 Core Value Proposition

```text
EXISTING CAMERAS
        +
EDGE AI
        +
EVENT INTELLIGENCE
        +
EXPLAINABLE RISK
        +
REAL-TIME COMMAND CENTER
        =
LOWER-COST INTELLIGENT SURVEILLANCE
```

## 1.3 Key Design Principle

> **Detection is not an incident.**

The system follows a strict hierarchy:

```text
OBSERVATION  →  EVENT  →  MULTIPLE EVENTS  →  INCIDENT
```

A single frame detection must never immediately trigger a security alert. Alerts require persistence, trajectory confirmation, and event correlation.

## 1.4 Target Hardware

| Machine | Role | Key Specs |
|---------|------|-----------|
| **Laptop 1** | AI Edge Node + Backend | Intel i5 13th Gen · 16 GB RAM · RTX 4050 6 GB VRAM |
| **Laptop 2** | Command Center Dashboard | Intel i5-1334U · 16 GB DDR4 · Intel Iris Xe |
| **Smartphones** | Temporary camera nodes + miniature command view | Any modern phone with camera + Wi-Fi |

---

# 2. System Architecture

## 2.1 High-Level Data Flow

```text
CCTV / IP / PHONE CAMERA
        │  RTSP / HTTP / MJPEG
        ▼
LAPTOP 1 — EDGE NODE (AI Inference)
        │  Structured Events (WebSocket / API)
        ▼
BACKEND (FastAPI + WebSocket Broker)
        │
        ├──► LAPTOP 2 — FULL DASHBOARD (Command Center)
        └──► SMARTPHONE — MINI DASHBOARD (LAN, via exposed Python port)
```

## 2.2 Edge Node Pipeline (Laptop 1)

```text
VIDEO INGESTION
   → PREPROCESSING (resize, ROI, frame sampling)
   → PERCEPTION (detection: person, vehicle, face, plate)
   → TRACKING (persistent IDs, trajectories)
   → EVENT ENGINE (virtual fence, zones, loitering, direction, night activity)
   → RISK & INCIDENT ENGINE (correlation, scoring, incident generation)
   → PUBLISH (structured events to backend)
```

## 2.3 Component Separation

The codebase must maintain strict separation of concerns:

| Layer | Responsibility | Location |
|-------|----------------|----------|
| Computer Vision | Detection, tracking, ANPR, face (no business logic) | `cv/` |
| Intelligence | Events, rules, risk, incidents (geometry + rules, not neural nets) | `intelligence/` |
| Video Pipelines | OpenCV / GStreamer / DeepStream backends | `pipelines/` |
| Edge App | AI inference node (Laptop 1) | `apps/edge/` |
| Backend | Event router, storage, REST API, WebSocket | `apps/backend/` |
| Dashboard | Command center UI (Laptop 2) | `apps/dashboard/` |

---

# 3. Functional Requirements

## 3.1 Camera Management (FR-01)

The system must support multiple camera source types:

- CCTV RTSP streams
- IP cameras
- Local video files
- HTTP / MJPEG streams
- **Smartphone camera streams** (prototype)

Each camera is represented by:

```json
{
  "camera_id": "BOP-CAM-01",
  "name": "Border Fence East",
  "source_url": "rtsp://...",
  "source_type": "rtsp",
  "status": "ONLINE",
  "location": { "lat": null, "lng": null },
  "inference_enabled": true
}
```

**Required operations:** add, remove, start, stop, reconnect, view health, assign name/location, configure zones/fences.

## 3.2 Perception (FR-02 to FR-04)

| ID | Capability | Notes |
|----|-----------|-------|
| FR-02 | Human detection | Bounding box + confidence |
| FR-03 | Vehicle detection & classification | car, motorcycle, bus, truck |
| FR-04 | Face detection | Optional, event-triggered only (not continuous) |
| FR-05 | ANPR | Event-triggered at checkpoints; OCR run once on best frame |

## 3.3 Tracking (FR-05)

Every detected object receives a persistent `track_id` with:

- Trajectory history
- Duration in frame
- Last-seen timestamp
- Zone membership
- Velocity approximation
- Crossing history

## 3.4 Spatial Intelligence (FR-06 to FR-09)

| ID | Capability | Description |
|----|-----------|-------------|
| FR-06 | Virtual fence | Operator-drawn line/polygon; crossing detection |
| FR-07 | Restricted zones | Safe / warning / restricted / no-entry zones |
| FR-08 | Loitering | Configurable time threshold in a zone |
| FR-09 | Direction detection | Allowed vs. forbidden movement direction |

## 3.5 Event Engine

Standalone layer (not embedded in CV code). Event taxonomy:

```text
PERSON_DETECTED, VEHICLE_DETECTED,
ZONE_ENTRY, ZONE_EXIT,
VIRTUAL_FENCE_CROSSING,
LOITERING, NIGHT_MOVEMENT,
VEHICLE_ENTERED_CHECKPOINT, ANPR_CAPTURED,
CAMERA_OFFLINE, CAMERA_RECOVERED,
HIGH_GPU_TEMPERATURE, INFERENCE_DEGRADED
```

## 3.6 Risk & Incident Engine

- Correlate multiple events into a single incident
- Compute an **explainable risk score** (0–100)
- Map score to severity: LOW (0–29), MEDIUM (30–59), HIGH (60–79), CRITICAL (80–100)
- Every incident must answer: **"Why did this alert fire?"**

Example incident:

```json
{
  "incident_id": "INC-000142",
  "camera_id": "BOP-CAM-01",
  "track_id": 42,
  "severity": "HIGH",
  "risk_score": 87,
  "contributing_events": [
    "restricted_zone_entry",
    "virtual_fence_crossing",
    "loitering",
    "night_time_activity"
  ]
}
```

## 3.7 Alerting & Notifications

- Dashboard alert (visual)
- Audio alert (optional)
- Real-time push to connected clients (desktop + mobile)
- Event logging / persistence

---

# 4. Dashboard (GUI) Requirements

## 4.1 Purpose

The dashboard is the **operator-facing command center**. It runs in a browser on Laptop 2 and consumes events, incidents, health metrics, and annotated streams from the backend. **It performs no AI inference.**

## 4.2 Dashboard Pages

### 4.2.1 Command Center (Default)

- Live camera grid (annotated feeds)
- Active incidents panel
- Recent alerts
- System health summary
- Quick camera status

### 4.2.2 Camera Management

- Add / edit / remove camera sources
- Start / stop / reconnect
- Configure resolution and inference rate
- Assign camera name and location

### 4.2.3 Camera Detail

- Live video with bounding boxes, track IDs, zones, virtual fences
- Draw / edit / delete polygons and fences
- Toggle annotation layers

### 4.2.4 Incident Center

- Searchable incident history
- Filters: severity, camera, date/time, event type, active/resolved
- Incident detail view with full event timeline and explainability breakdown

### 4.2.5 Map View

- Camera pins with online/offline status
- Active incident markers (color-coded by severity)
- Logical surveillance zones
- (Prototype may use simulated/demo coordinates)

### 4.2.6 System Health

- GPU utilization, VRAM, temperature
- CPU / RAM usage
- Inference FPS and latency
- Dropped frame rate, queue depth
- Per-camera connection status

## 4.3 Dashboard Layout (Reference)

```text
┌──────────────────────────────────────────────────────────────┐
│ IBVAP COMMAND CENTER                         ● SYSTEM ONLINE │
├──────────────┬──────────────────────────┬────────────────────┤
│ CAMERA LIST  │      LIVE CAMERA GRID    │ ACTIVE INCIDENTS   │
│ CAM-01 🟢    │   ┌──────────────────┐   │ 🔴 HIGH            │
│ CAM-02 🟢    │   │  Annotated Feed  │   │ Border Intrusion   │
│ CAM-03 🔴    │   │                  │   │ Risk: 87           │
│              │   └──────────────────┘   │ 🟠 MEDIUM          │
├──────────────┴──────────────────────────┴────────────────────┤
│ EVENT TIMELINE                                                │
│ 18:22 Fence crossing · CAM-01                                │
│ 18:21 Restricted zone entry · CAM-01                         │
├──────────────────────────────────────────────────────────────┤
│ SYSTEM HEALTH                                                 │
│ GPU 78% │ VRAM 4.2/6GB │ TEMP 71°C │ FPS 12 │ DROP 0.4%      │
└──────────────────────────────────────────────────────────────┘
```

## 4.4 Video Streaming Strategy

The dashboard must **not** consume RTSP directly. The edge node processes and annotates frames, then serves them via an output adapter:

```text
RTSP CAMERA → EDGE NODE → PROCESS + ANNOTATE → MJPEG ENDPOINT
```

Example endpoint: `http://192.168.x.x:8000/streams/BOP-CAM-01`

**Phase 1 recommendation:** MJPEG (simple, browser-compatible, LAN-friendly). WebRTC is deferred.

---

# 5. GUI Locations & Behavior

## 5.1 Where GUIs Are Needed

| # | GUI | Location | Purpose |
|---|-----|----------|---------|
| 1 | **Full Command Center** | Laptop 2 (browser) | Primary operator interface: live feeds, incidents, map, analytics, admin |
| 2 | **Miniature Dashboard** | Smartphone (browser, LAN) | Operator awareness: alerts, active incidents, single camera stream |
| 3 | **Camera Configuration** | Laptop 2 (within dashboard) | Add/configure cameras, draw fences/zones |
| 4 | **System Health** | Laptop 2 (within dashboard) | Monitor GPU/CPU/VRAM/FPS/queue |

## 5.2 GUI Behavior Rules

- **Laptop 2 dashboard** = full-featured command center (all pages in §4.2).
- **Smartphone dashboard** = lightweight awareness screen (see §7), not the full command center.
- Both GUIs are **responsive web applications** served by the same backend — no separate native mobile app.
- Both connect to the backend via **WebSocket** for real-time updates.
- The dashboard must support a **mock data mode** so UI development proceeds independently of the AI pipeline.

---

# 6. Smartphone as CCTV Camera

## 6.1 Concept

For the prototype, a smartphone acts as a **temporary IP camera** — it captures video and streams it to the edge node over LAN/Wi-Fi. The phone does **not** perform AI processing.

## 6.2 Connection Flow

```text
SMARTPHONE CAMERA
       │  Camera streaming app
       ▼
Wi-Fi / Local LAN
       │
       ▼
http://LAPTOP_IP:CAMERA_PORT/stream   (or rtsp://PHONE_IP:PORT/stream)
       │
       ▼
IBVAP CAMERA INGESTION (edge node)
       │
       ▼
AI EDGE PIPELINE
```

## 6.3 Generic Camera Source Adapter

To avoid coupling to any single phone-streaming app, the ingestion layer must accept a **generic source adapter** supporting:

```text
RTSP
HTTP Video Stream
MJPEG
USB Webcam
Local Video
```

A phone is then simply **another source type**. This prevents rework if a phone-streaming app behaves unexpectedly during the demo.

## 6.4 Demo Setup Example

```text
Phone 1 (points at "border area")
   → streams over Wi-Fi
   → Laptop 1 receives stream
   → runs detection, tracking, intrusion detection
   → generates incident
   → alert pushed to Laptop 2 dashboard + phone mini dashboard
```

---

# 7. Miniature Smartphone Dashboard (LAN)

## 7.1 Concept

A **responsive version of the same web application**, accessible from a smartphone browser over the local network. It is an **operator awareness screen**, not the full command center.

## 7.2 LAN Connection via Exposed Python Port

The backend (FastAPI/Uvicorn) must bind to `0.0.0.0` so LAN devices can connect:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Connection example:

```text
Laptop IP: 192.168.1.10
Phone URL: http://192.168.1.10:8000
```

The same exposed port serves both the full dashboard and the responsive mini dashboard (responsive CSS / media queries).

## 7.3 Mini Dashboard Features (Top Priority)

- System status indicator (LIVE / OFFLINE)
- Active incidents with severity
- Camera selector
- Single live camera stream
- Acknowledge incident action

Reference layout:

```text
┌───────────────────────┐
│ IBVAP        🟢 LIVE  │
├───────────────────────┤
│     LIVE CAMERA       │
├───────────────────────┤
│ 🔴 HIGH INCIDENT      │
│ CAM-01                │
│ Risk Score: 87        │
│ [ACKNOWLEDGE]         │
├───────────────────────┤
│ 🟢 CAM-01             │
│ 🟢 CAM-02             │
│ 🔴 CAM-03 OFFLINE     │
└───────────────────────┘
```

## 7.4 Excluded from Mobile (Initially)

- Polygon / fence editing
- Complex analytics and charts
- Configuration screens
- Multi-camera grids

---

# 8. Backend & API Requirements

## 8.1 Technology

```text
FastAPI + Uvicorn
WebSockets (starlette)
Pydantic (event validation)
SQLite (dev) → PostgreSQL (production, if needed)
```

## 8.2 REST API

```text
GET    /health
GET    /cameras
POST   /cameras
DELETE /cameras/{id}
POST   /cameras/{id}/start
POST   /cameras/{id}/stop
POST   /cameras/{id}/reconnect
GET    /incidents
GET    /incidents/{id}
POST   /incidents/{id}/acknowledge
GET    /events
GET    /metrics
POST   /cameras/{id}/zones
POST   /cameras/{id}/fence
WS     /ws/events
WS     /ws/metrics
```

## 8.3 Real-Time Communication

```text
EDGE NODE → BACKEND → (save + broadcast via WebSocket)
                              ├──► DESKTOP DASHBOARD
                              └──► MOBILE DASHBOARD
```

The backend must **deduplicate events** before broadcasting.

## 8.4 Time Architecture (Three Clocks)

Each event stores three timestamps to debug latency:

- `capture_ts` — when the camera frame was captured
- `ingest_ts` — when the edge node processed it
- `display_ts` — when the dashboard received it

---

# 9. Non-Functional Requirements

## 9.1 Reliability

- Camera reconnection (RTSP watchdog)
- Bounded frame queues (drop stale frames)
- Graceful degradation
- Health checks

## 9.2 Performance Targets (RTX 4050)

| Metric | Target |
|--------|--------|
| Active AI cameras | 1–3 |
| Camera input | 1080p acceptable |
| Inference resolution | ~640 |
| AI processing | 8–15 FPS |
| Dashboard latency | < 2 seconds preferred |
| Sustained runtime | 30–60 minutes |
| VRAM | Controlled below limit |
| Queue growth | Near zero |

## 9.3 Usability

An operator must understand within seconds:

```text
What happened?  Where?  When?  How severe?  Why did the system think it mattered?
```

## 9.4 Maintainability

Preserve separation between `cv/`, `intelligence/`, `pipelines/`, `apps/edge/`, `apps/backend/`, `apps/dashboard/`. No monolithic `main.py`.

## 9.5 Resource Management Rules

**Never** run YOLO + face + ANPR + OCR + ReID on every frame. Use event-triggered expensive tasks:

```text
VEHICLE DETECTED → Checkpoint? → Collect candidate frames → Select best → ANPR → OCR once
```

---

# 10. Out of Scope (Initial)

- Full biometric facial recognition database
- Sophisticated person ReID (unless necessary)
- Multi-site cloud deployment / Kubernetes
- Authentication microservices
- Distributed Kafka architecture
- 20-camera stress testing
- LLM-powered suspicious activity detection
- WebRTC before MJPEG works
- DeepStream before the Python pipeline works
- PostgreSQL before SQLite becomes insufficient

---

# 11. MVP Definition

The minimum convincing prototype must demonstrate:

**Camera**
- [ ] Smartphone camera connected over LAN
- [ ] At least one additional camera/video source
- [ ] Camera online/offline detection

**AI**
- [ ] Person detection
- [ ] Vehicle detection
- [ ] Object tracking

**Intelligence**
- [ ] Virtual fence
- [ ] Restricted zone
- [ ] Temporal confirmation
- [ ] Loitering
- [ ] Risk scoring
- [ ] Incident generation

**Dashboard**
- [ ] Live annotated feed
- [ ] Active incidents
- [ ] Incident explanation
- [ ] Timeline
- [ ] Camera health
- [ ] GPU metrics

**Mobile**
- [ ] Phone-accessible dashboard (LAN, exposed Python port)
- [ ] Real-time alerts
- [ ] Active incident view
- [ ] Single camera stream

---

# 12. Development Phases

| Phase | Focus | Done When |
|-------|-------|-----------|
| 1 | Camera ingestion (webcam, local video, RTSP, phone stream) | One phone → Laptop → live frame works reliably |
| 2 | Detection (person, vehicle) | Bounding boxes + confidence + class |
| 3 | Tracking (ByteTrack/BoT-SORT) | Stable track IDs + trajectory |
| 4 | Virtual fence | Person + track + fence crossing = event |
| 5 | Event intelligence (loitering, zones, direction, cooldowns) | Temporal confirmation works |
| 6 | Risk + incident engine | Events → correlation → risk → incident |
| 7 | Backend (FastAPI, SQLite, REST, WebSocket) | Edge → Backend → Mock UI works |
| 8 | Full dashboard (with mock mode) | Command center functional |
| 9 | Mobile dashboard (responsive, LAN) | Phone browser shows live alerts + stream |
| 10 | Optimization (FP16 → ONNX → TensorRT) | Only after system works |

---

## Appendix: Strong SIH Demo Story

```text
1.  Smartphone acts as an existing surveillance camera.
2.  Person approaches the simulated border.
3.  AI detects the person.
4.  Tracker follows the person.
5.  Person enters a warning zone.
6.  Person remains there (loitering event).
7.  Person crosses the virtual fence.
8.  Event engine correlates behaviour.
9.  Risk score increases.
10. Incident is generated.
11. Laptop 2 dashboard receives the alert.
12. Incident explanation shows WHY.
13. A smartphone on the same LAN also receives the alert.
14. System health demonstrates the prototype runs locally on constrained hardware.
```

That is a coherent **end-to-end product demonstration** — not merely "YOLO detecting a person."

# Project Context: SIH 2026 – AI-Based Intelligent Border Video Analytics Platform

> This document captures the complete technical context and strategic discussion for the selected Smart India Hackathon 2026 problem statement.
>
> The goal is to provide enough context for another AI agent, developer, teammate, or coding environment to continue the project without needing the previous conversation.

---

# 1. Selected Problem Statement

## Problem Statement ID

**SIH26187**

## Title

**AI-Based Intelligent Video Analytics Platform for Border Surveillance using Existing CCTV Infrastructure**

## Organization

**Ministry of Home Affairs**

## Department

**Sashastra Seema Bal (SSB), Police II Division**

## Category

**Software**

## Theme

**Smart Automation**

---

# 2. Original Problem Statement Summary

Border security forces deploy CCTV cameras at:

- Border Out Posts (BOPs)
- Check posts
- Border roads
- Strategic locations

Traditional CCTV systems mainly provide:

- Live video
- Video recording

These systems require continuous human monitoring.

The challenge is to transform existing standard IP-based CCTV infrastructure into an intelligent AI-powered surveillance system without requiring expensive dedicated hardware such as:

- Smart cameras
- Dedicated facial recognition hardware
- Dedicated ANPR hardware

The system should process live video streams and provide capabilities including:

- Human detection and tracking
- Vehicle detection and classification
- Face detection
- Automatic Number Plate Recognition (ANPR)
- Virtual fence intrusion detection
- Suspicious activity detection
- Night-time movement detection
- Real-time alert generation
- Event logging

The final system should:

- Work with existing CCTV infrastructure
- Be cost-effective
- Be scalable
- Be suitable for remote border locations
- Support integration with existing command and control systems
- Improve situational awareness
- Reduce response time

---

# 3. Initial Strategic Assessment

The problem is considered technically challenging but highly feasible for a strong prototype.

The biggest advantage is that many of the individual technical components already exist:

- Object detection models
- Object tracking models
- Face detection models
- ANPR models
- Video analytics frameworks
- TensorRT optimization
- DeepStream
- GStreamer
- Existing open-source repositories

Therefore, the main challenge is **not inventing every AI model from scratch**.

The real challenge is:

> Building a reliable, efficient, real-time architecture that combines these components into a meaningful border intelligence platform.

The project should not become:

> "We ran YOLO on a CCTV feed."

That is not enough.

The project should instead demonstrate:

```text
Raw Video
    ↓
Detection
    ↓
Tracking
    ↓
Understanding of Spatial Context
    ↓
Temporal Event Detection
    ↓
Event Correlation
    ↓
Risk Assessment
    ↓
Incident Generation
    ↓
Command Center Alert
````

The differentiation should come from the **event intelligence and incident generation layer**, not merely object detection.

---

# 4. Available Hardware

The team does not have heavy workstation-class systems.

Two laptops are available.

---

## Laptop 1: AI / Edge Processing Machine

### Specifications

* CPU: Intel Core i5, 13th Generation
* RAM: 16 GB
* GPU: NVIDIA RTX 4050 Laptop GPU
* VRAM: 6 GB

### Proposed Role

Laptop 1 should act as the:

```text
AI Edge Processing Node
```

Responsibilities:

* Video ingestion
* CCTV stream decoding
* Object detection
* Object tracking
* Virtual fence analysis
* Event generation
* Risk scoring
* ANPR when required
* Optional face detection
* AI inference
* TensorRT execution
* DeepStream/GStreamer pipeline in later stages

This is the primary compute machine.

---

## Laptop 2: Command Center / Dashboard Machine

### Specifications

* CPU: Intel Core i5-1334U
* RAM: 16 GB DDR4-3200
* GPU: Intel Iris Xe Graphics

### Proposed Role

Laptop 2 should act as:

```text
Command & Control Center
```

Responsibilities:

* Web dashboard
* Live camera display
* Incident visualization
* Event timeline
* Maps
* Alerts
* Analytics
* System health monitoring
* Administrative controls

Laptop 2 should not be relied upon as the primary AI inference machine.

However, Intel OpenVINO may be explored for lightweight workloads or fallback scenarios.

---

# 5. High-Level Hardware Architecture

```text
                    ┌─────────────────────────────┐
                    │        CCTV CAMERAS         │
                    │                             │
                    │ RTSP / IP Camera / Video    │
                    └──────────────┬──────────────┘
                                   │
                                   │ LAN / Wi-Fi
                                   ▼
                    ┌─────────────────────────────┐
                    │          LAPTOP 1           │
                    │                             │
                    │ RTX 4050 – 6 GB VRAM        │
                    │                             │
                    │ AI EDGE PROCESSING NODE     │
                    │                             │
                    │ • Video Processing          │
                    │ • Detection                 │
                    │ • Tracking                  │
                    │ • Event Engine              │
                    │ • Risk Engine               │
                    │ • TensorRT                  │
                    └──────────────┬──────────────┘
                                   │
                                   │ Structured Events
                                   │ WebSocket / API
                                   ▼
                    ┌─────────────────────────────┐
                    │          LAPTOP 2           │
                    │                             │
                    │ COMMAND CENTER              │
                    │                             │
                    │ • Dashboard                 │
                    │ • Alerts                    │
                    │ • Maps                      │
                    │ • Incident Timeline         │
                    │ • System Monitoring         │
                    └─────────────────────────────┘
```

---

# 6. Core Product Concept

The project should be positioned as a:

# Software-Defined Intelligent Border Surveillance Platform

Possible project name:

```text
IBVAP

Intelligent Border Video Analytics Platform
```

Alternative branding may be explored later.

The core idea:

> Existing CCTV cameras become intelligent sensors through AI software.

Instead of requiring border personnel to continuously watch multiple video feeds, the system automatically identifies meaningful events.

---

# 7. Complete Prototype Workflow

The final prototype architecture should follow this pipeline:

```text
CCTV CAMERA
    │
    │ RTSP / IP Stream
    ▼
VIDEO INGESTION LAYER
    │
    ├── RTSP Stream Handler
    ├── Protocol Management
    ├── Frame Decoding
    └── Buffer Management
    │
    ▼
PREPROCESSING & OPTIMIZATION
    │
    ├── Resize
    ├── Normalize
    ├── Frame Sampling
    ├── Region of Interest
    └── Optional Low-Light Enhancement
    │
    ▼
PERCEPTION ENGINE
    │
    ├── Human Detection
    ├── Vehicle Detection
    ├── Vehicle Classification
    ├── Face Detection
    ├── Number Plate Detection
    └── Multi-Object Tracking
    │
    ▼
EVENT ENGINE
    │
    ├── Virtual Fence
    ├── Restricted Zone Entry
    ├── Line Crossing
    ├── Direction Detection
    ├── Loitering
    ├── Night-Time Activity
    └── Suspicious Pattern Detection
    │
    ▼
INTELLIGENCE / RISK ENGINE
    │
    ├── Event Correlation
    ├── Risk Scoring
    ├── False Alarm Filtering
    ├── Incident Generation
    └── Explainable Alert Reason
    │
    ▼
ALERT & NOTIFICATION ENGINE
    │
    ├── Dashboard Alert
    ├── Audio Alert
    ├── Visual Alert
    ├── Mobile Notification
    └── Event Logging
    │
    ▼
DATA MANAGEMENT
    │
    ├── Event Database
    ├── Incident History
    ├── Video Evidence
    ├── Metadata
    └── Analytics
```

---

# 8. Perception Engine

The perception engine is responsible for understanding what exists in the camera frame.

The initial architecture should include:

```text
VIDEO FRAME
    │
    ▼
OBJECT DETECTOR
    │
    ├── Person
    ├── Vehicle
    └── Other Relevant Objects
    │
    ▼
MULTI-OBJECT TRACKER
    │
    ├── Track ID: 1
    ├── Track ID: 2
    └── Track ID: 3
```

Example:

```text
Person enters frame

Frame 1:
Person → ID 23

Frame 2:
Same Person → ID 23

Frame 3:
Same Person → ID 23
```

The tracking system allows the platform to understand movement over time.

---

# 9. Virtual Fence Detection

A major feature of the prototype will be:

# AI-Based Virtual Border Fence

Instead of requiring a physical sensor, the operator defines a virtual boundary.

Example:

```text
Camera View

         SAFE AREA

              Person

------------------------------
       VIRTUAL BORDER LINE
------------------------------

       RESTRICTED AREA
```

The system tracks the person's trajectory.

If the tracked object crosses the virtual boundary:

```text
Person ID: 23

Position A
    ↓
Position B
    ↓
Crosses Virtual Border
    ↓

EVENT:
BORDER INTRUSION DETECTED
```

The event engine should verify:

* Object type
* Object confidence
* Track persistence
* Actual line crossing
* Direction of movement

This reduces false alarms.

---

# 10. Example Border Intrusion Recognition Flow

The prototype demo should visually demonstrate:

```text
STEP A
Original CCTV Frame
```

A person approaches a border fence.

```text
STEP B
Human Detection
```

The AI model detects:

```text
Person
Confidence: 0.92
```

A bounding box is drawn around the person.

```text
STEP C
Tracking
```

The tracker assigns:

```text
TRACK ID: 23
```

The system now understands that the person is the same individual across multiple frames.

```text
STEP D
Virtual Fence Analysis
```

The person's trajectory approaches the defined border line.

```text
STEP E
Line Crossing
```

The person crosses the defined boundary.

```text
STEP F
Event Trigger
```

The event engine generates:

```text
INCIDENT #014

TYPE:
Border Intrusion

CAMERA:
BOP-CAM-01

TRACK ID:
23

TIME:
Timestamp

CONFIDENCE:
0.92
```

If additional suspicious signals exist:

```text
Restricted Zone Entry
+
Loitering
+
Night-Time Activity
```

Then:

```text
HIGH-RISK INCIDENT

Risk Score: 87/100
```

---

# 11. Important Design Principle: Detection Is Not an Incident

This distinction is critical.

A raw AI detection:

```text
Person detected
```

is not automatically a security incident.

It is only an:

```text
Observation
```

The system should follow:

```text
OBSERVATION

Person detected
        │
        ▼

EVENT

Restricted zone entered
        │
        ▼

MULTIPLE EVENTS

Restricted entry
+
Loitering
+
Night activity
        │
        ▼

INCIDENT

High-Risk Border Intrusion
```

This event hierarchy should be a major architectural component.

---

# 12. Event Intelligence Engine

The event engine should not be a collection of random `if` statements.

It should have a structured architecture.

```text
Detection
    │
    ▼
Event Normalization
    │
    ▼
Rule Evaluation
    │
    ├── Zone Rule
    ├── Line Rule
    ├── Time Rule
    └── Behavioral Rule
    │
    ▼
Event Correlation
    │
    ▼
Risk Scoring
    │
    ▼
Incident Generation
```

Example:

```text
Event 1:
Person enters restricted zone

Event 2:
Person remains for 30 seconds

Event 3:
Person approaches border fence

Event 4:
Person crosses virtual boundary
```

The system correlates them.

```text
INCIDENT:
Suspicious Border Crossing

Risk Score: HIGH
```

---

# 13. Risk Scoring

A simple explainable risk engine should initially be used instead of an unnecessarily complex ML model.

Example:

```text
Restricted Zone Entry      +30

Virtual Fence Crossing     +40

Loitering                  +15

Night-Time Activity        +20

Vehicle Match              +10
```

Example:

```text
30 + 40 + 20 = 90
```

Final:

```text
RISK SCORE: 90/100

SEVERITY: CRITICAL
```

The exact scoring logic can be improved later.

The important point:

> Judges should understand why the system raised an alert.

---

# 14. Technology Stack

## Prototype Development

Initial development:

```text
Python
OpenCV
PyTorch
YOLO-family detector
ByteTrack / BoT-SORT
Supervision
FastAPI
WebSocket
PostgreSQL
React / Next.js
Leaflet
```

---

## Optimization Stack

```text
PyTorch Model
      ↓
ONNX
      ↓
TensorRT
      ↓
FP16
      ↓
Optimized RTX 4050 Inference
```

---

## Production Video Pipeline

Later:

```text
GStreamer
+
NVIDIA DeepStream
+
TensorRT
+
NVIDIA Hardware Decode
```

---

# 15. Open-Source Projects and Frameworks Worth Studying

## NVIDIA DeepStream

Primary importance:

* Multi-stream analytics
* GStreamer pipelines
* TensorRT inference
* Object tracking
* Hardware video decoding
* Metadata management
* Video analytics

Useful features relevant to this project:

* ROI filtering
* Line crossing
* Direction detection
* Object tracking
* Multi-stream support

Important strategic decision:

> Do not begin the project directly with DeepStream.

Reason:

DeepStream adds complexity involving:

* GStreamer
* CUDA
* TensorRT
* Drivers
* Docker
* Model conversion

The initial algorithm should first be validated using a simpler Python pipeline.

---

## NVIDIA TensorRT

Used for:

* Model optimization
* FP16 inference
* Potential INT8 inference
* Reduced latency
* Faster GPU inference

Optimization pipeline:

```text
PyTorch
    ↓
ONNX
    ↓
TensorRT FP16
```

FP16 should be attempted before INT8.

INT8 should only be used if necessary because calibration and accuracy validation become more complex.

---

## Ultralytics / YOLO Ecosystem

Useful for:

* Object detection
* Tracking
* Rapid experimentation
* TensorRT export

Potential tracking options:

```text
ByteTrack
BoT-SORT
```

Licensing must be reviewed carefully before final submission or future commercialization.

---

## Roboflow Supervision

Useful during rapid prototyping for:

* Zones
* Polygon regions
* Line crossing
* Tracking visualization
* Counting
* Video utilities

Recommended mainly for:

```text
Prototype Phase
```

---

## Norfair

Useful as a lightweight alternative for experimentation with:

* Multi-object tracking
* Custom tracking logic

Not necessarily required for the final architecture.

---

## Frigate

Useful for studying:

* Real-world video analytics architecture
* Camera management
* Hardware acceleration
* Event processing
* Multiple camera handling

Important because it demonstrates how real systems handle the boring but deadly engineering problems.

---

## OpenVINO

Relevant mainly to:

```text
Laptop 2
Intel CPU
Intel Iris Xe
```

Possible uses:

* Lightweight inference
* Fallback workloads
* CPU/iGPU experiments

Laptop 2 should not be the primary inference machine.

---

# 16. AirLLM Decision

AirLLM was considered as a possible optimization strategy.

Final decision:

> AirLLM should not be part of the critical path.

Reason:

The primary workload of SIH26187 is:

```text
Computer Vision
+
Real-Time Video Analytics
```

not large language model inference.

The real optimization stack should focus on:

```text
Frame Scheduling
        ↓
Resolution Optimization
        ↓
Smaller Efficient Models
        ↓
FP16
        ↓
TensorRT
        ↓
Hardware Video Decoding
        ↓
Pipeline Parallelism
        ↓
DeepStream
```

An LLM may later be used for optional:

* Incident report generation
* Natural language querying
* Event summaries

But it must not sit in the real-time detection loop.

---

# 17. Development Strategy

The project should be developed in phases.

---

# Phase 0: Hardware Benchmarking

Before building the entire application:

Prepare Laptop 1 as a reproducible benchmarking machine.

Install and validate:

```text
CUDA
PyTorch
ONNX
TensorRT
OpenCV
FFmpeg
GStreamer
```

Benchmark:

```text
GPU utilization
VRAM
CPU utilization
RAM
FPS
Inference latency
GPU temperature
```

Create a benchmark table:

| Model   | Resolution | Backend       | FPS | Latency | VRAM | GPU % | CPU % |
| ------- | ---------: | ------------- | --: | ------: | ---: | ----: | ----: |
| Model A |        640 | PyTorch       | TBD |     TBD |  TBD |   TBD |   TBD |
| Model A |        640 | ONNX          | TBD |     TBD |  TBD |   TBD |   TBD |
| Model A |        640 | TensorRT FP16 | TBD |     TBD |  TBD |   TBD |   TBD |

No optimization decisions should be based purely on assumptions.

---

# Phase 1: Single Camera Detection

Build:

```text
One Video
    ↓
One Detector
    ↓
Bounding Boxes
```

Success criteria:

* Stable detection
* No memory leak
* Stable FPS
* No crashes

Test different resolutions:

```text
640×360
640×480
640×640
960×540
1280×720
```

Find the best accuracy/performance tradeoff.

---

# Phase 2: Object Tracking

Add:

```text
Detector
    ↓
Tracker
    ↓
Persistent Track IDs
```

Success criteria:

* Same object retains identity
* Acceptable ID switches
* Stable tracking

---

# Phase 3: Event Engine

Implement:

## Virtual Fence

```text
Person
    ↓
Trajectory
    ↓
Boundary Intersection
    ↓
Intrusion Event
```

## Line Crossing

```text
Object moves
A → B

Crosses line
    ↓

Event Generated
```

## Loitering

```text
Object enters ROI
        ↓
Timer starts
        ↓
Object remains
        ↓
Threshold exceeded
        ↓
Loitering Event
```

## Direction Detection

```text
Track Trajectory
        ↓
Movement Vector
        ↓
Expected / Forbidden Direction
```

Most of these features are geometry and temporal logic.

They should not unnecessarily consume GPU resources.

---

# Phase 4: Incident & Risk Engine

Implement:

```text
Observations
       ↓
Events
       ↓
Event Correlation
       ↓
Risk Score
       ↓
Incident
```

This is where the project becomes more than a detection demo.

---

# Phase 5: Vehicle Intelligence and ANPR

Pipeline:

```text
Vehicle Detection
        ↓
Vehicle Tracking
        ↓
Plate ROI
        ↓
Collect Candidate Frames
        ↓
Select Best Frame
        ↓
Plate Detection
        ↓
OCR
        ↓
Validation
```

Critical rule:

> Do not run OCR on every frame.

Instead:

```text
Vehicle enters checkpoint
        ↓
Collect several frames
        ↓
Select best plate image
        ↓
Run OCR once
```

This saves GPU resources.

---

# Phase 6: Night-Time Performance

First benchmark the normal detector.

```text
Daylight Dataset
        ↓
Measure

Night Dataset
        ↓
Measure
```

If performance degradation is significant:

Possible approaches:

```text
Low-Light Enhancement
        ↓
Detector
```

or:

```text
Fine-Tune Small Detector
on Night / Low-Light Dataset
```

Do not immediately add a massive specialized model.

---

# Phase 7: TensorRT Optimization

Only after the baseline system works.

Pipeline:

```text
PyTorch
    ↓
ONNX Export
    ↓
TensorRT FP16
```

Benchmark:

| Model    | Backend       | FPS | Latency | VRAM |
| -------- | ------------- | --: | ------: | ---: |
| Detector | PyTorch FP32  | TBD |     TBD |  TBD |
| Detector | PyTorch FP16  | TBD |     TBD |  TBD |
| Detector | ONNX          | TBD |     TBD |  TBD |
| Detector | TensorRT FP16 | TBD |     TBD |  TBD |

The winning configuration should be selected based on actual measurements.

---

# Phase 8: DeepStream Migration

Only migrate after:

```text
Detection works
Tracking works
Events work
Risk engine works
```

Then:

```text
Python Prototype
        ↓
Validated Architecture
        ↓
GStreamer / DeepStream
```

DeepStream should help optimize:

* Multi-camera pipelines
* Hardware decoding
* TensorRT inference
* Metadata handling
* GPU memory flow

Do not use DeepStream before the core logic is understood.

---

# 18. Optimization Philosophy

The optimization ladder:

```text
1. Eliminate unnecessary processing
        ↓
2. Reduce frame frequency where possible
        ↓
3. Reduce inference resolution
        ↓
4. Choose efficient models
        ↓
5. FP16
        ↓
6. TensorRT
        ↓
7. Hardware video decoding
        ↓
8. Pipeline parallelism
        ↓
9. INT8 if necessary
        ↓
10. Advanced multi-stream optimization
```

The most important optimization principle:

> Do not run expensive AI on every frame unless absolutely necessary.

Example:

Camera:

```text
30 FPS
```

AI detection might operate at:

```text
8–15 FPS
```

Tracking fills temporal continuity.

Expensive tasks should be event-triggered:

```text
ANPR
→ Only near checkpoint

Face Detection
→ Only when useful

Risk Analysis
→ Event-driven

LLM
→ Report generation only
```

---

# 19. Hardware Video Decoding

Avoid:

```text
Camera
    ↓
CPU Decode
    ↓
RAM Copy
    ↓
GPU Inference
```

Prefer:

```text
Camera
    ↓
Hardware Decode
    ↓
GPU Pipeline
    ↓
TensorRT
```

The goal is to avoid wasting CPU resources decoding multiple high-resolution streams.

---

# 20. Multi-Camera Strategy

Do not immediately attempt:

```text
10 Cameras
```

Benchmark gradually:

```text
1 Camera
    ↓
2 Cameras
    ↓
3 Cameras
```

Potential strategy:

```text
Camera Resolution:
1920×1080

Inference Resolution:
640×640

Dashboard:
1920×1080
```

The original camera stream does not need to be fed to the detector at full resolution.

---

# 21. Major Expected Bottlenecks

## 1. VRAM Pressure

Laptop 1 has:

```text
RTX 4050
6 GB VRAM
```

Potential memory consumers:

* Detector
* Tracker/ReID
* ANPR
* Face model
* TensorRT workspace
* CUDA buffers
* Video frames

Possible result:

```text
CUDA OUT OF MEMORY
```

Strategy:

* Keep only critical models resident
* Load secondary models only when necessary
* Use small efficient models
* Use FP16
* Monitor VRAM

---

## 2. Thermal Throttling

The prototype will run on a laptop.

Short benchmarks are insufficient.

Run:

```text
30–60 minutes continuous inference
```

Measure:

* Temperature
* GPU clock
* FPS
* VRAM
* CPU

A model that works at 30 FPS for 20 seconds but drops to 8 FPS after heating is not production-ready.

---

## 3. Video Decoding

Multiple 1080p streams can create heavy CPU load if hardware decoding is not enabled.

Benchmark:

```text
Decode CPU usage
```

separately from:

```text
AI inference
```

---

## 4. Frame Queue Explosion

Example:

```text
Camera = 30 FPS
AI = 8 FPS
```

If every frame is queued:

```text
Frame 1
Frame 2
Frame 3
...
Frame 500
```

The AI eventually processes old frames.

That is not real-time.

Use:

```text
Bounded Queue
or
Latest Frame Strategy
```

Drop stale frames.

Current information is more valuable than processing every historical frame.

---

## 5. RTSP Instability

Real cameras may:

* Disconnect
* Freeze
* Send corrupt frames
* Change timestamps
* Change resolution
* Lose packets

Need:

```text
RTSP Watchdog
        ↓
Connection Failure
        ↓
Automatic Reconnect
        ↓
Pipeline Restart
        ↓
Resume Processing
```

---

## 6. Tracker ID Switches

Example:

```text
Person #17
        ↓
Occlusion
        ↓
Person #29
```

The tracker mistakenly treats the same person as a new individual.

Mitigation:

* Tune tracking thresholds
* Tune track buffer
* Use temporal confirmation
* Consider ReID only if required
* Do not trigger severe incidents based on one frame

---

## 7. False Positives

Example:

```text
Moving tree
    ↓
False person detection
    ↓
Virtual fence event
    ↓
False border intrusion
```

Mitigation:

```text
Single Detection
        ↓
Ignore / Candidate

Persistent Detection
        ↓
Candidate Event

Trajectory Confirmation
        ↓
Actual Event
```

False alarm control is one of the highest-priority challenges.

---

## 8. ANPR Reliability

Problems:

* Motion blur
* Dirty plates
* Low resolution
* Oblique angle
* Night conditions
* Headlights
* Compression artifacts

Never claim:

```text
98% Accuracy
```

unless it is measured.

Separate:

```text
Plate Detection Accuracy

and

OCR Exact Match Accuracy
```

---

# 22. Expected Bugs

Maintain:

```text
KNOWN_ISSUES.md
```

Potential categories:

## Video

* RTSP timeout
* Frozen frames
* Decode failures
* FPS collapse
* Timestamp mismatch
* Reconnection failures

## GPU

* CUDA out of memory
* TensorRT engine build failures
* Unsupported ONNX operations
* CUDA version mismatch
* TensorRT version mismatch
* Wrong GPU selected

## Tracking

* ID switches
* Track fragmentation
* Ghost tracks
* Duplicate tracks
* Lost tracks

## ANPR

* Incorrect plate crop
* OCR mistakes
* Character confusion
* Night failures

## Event Engine

* Duplicate alerts
* Alert spam
* Incorrect loitering duration
* Fence geometry errors
* False intrusion
* Race conditions

## Backend

* WebSocket disconnect
* Duplicate events
* Database locking
* Dashboard synchronization delays

## Deployment

* Missing CUDA libraries
* Missing TensorRT libraries
* Docker GPU passthrough problems
* Incompatible TensorRT engines

---

# 23. The Three Clocks Problem

The system may have:

```text
Camera Clock
        +
Processing Clock
        +
Dashboard Clock
```

These timestamps can differ.

Each event should ideally store:

```json
{
    "event_id": "INC-000142",
    "camera_id": "CAM-01",
    "capture_ts": "timestamp",
    "ingest_ts": "timestamp",
    "event_ts": "timestamp",
    "display_ts": "timestamp"
}
```

For the prototype, server-side ingestion timestamps may be more reliable than assuming all cameras have synchronized clocks.

---

# 24. Observability

The system should expose internal performance metrics.

Important metrics:

```text
FPS
Inference Latency
Queue Depth
Dropped Frames
GPU Utilization
VRAM Usage
CPU Usage
RAM Usage
GPU Temperature
Camera Status
Detector Status
Tracker Status
```

Example dashboard:

```text
SYSTEM HEALTH

GPU
78%

VRAM
4.2 / 6 GB

TEMPERATURE
71°C

CAM-01
ONLINE

CAM-02
ONLINE

INFERENCE
11.7 FPS

DROPPED FRAMES
0.4%

QUEUE DEPTH
1
```

This helps both development and SIH judging.

---

# 25. Suggested Repository Structure

```text
ibvap/
│
├── apps/
│   ├── edge/
│   ├── backend/
│   └── dashboard/
│
├── cv/
│   ├── detection/
│   ├── tracking/
│   ├── anpr/
│   ├── face/
│   └── preprocessing/
│
├── intelligence/
│   ├── events/
│   ├── rules/
│   ├── risk/
│   └── incidents/
│
├── pipelines/
│   ├── opencv/
│   ├── gstreamer/
│   └── deepstream/
│
├── models/
│   ├── pytorch/
│   ├── onnx/
│   └── tensorrt/
│
├── datasets/
│   ├── raw/
│   ├── annotations/
│   ├── processed/
│   └── splits/
│
├── benchmarks/
│
├── configs/
│
├── scripts/
│
├── tests/
│
├── docker/
│
├── docs/
│
├── README.md
├── LICENSE
└── pyproject.toml
```

Important principle:

> Model implementation must not be tightly coupled to business/event logic.

Example abstraction:

```text
Detector
    │
    ├── YOLODetector
    ├── ONNXDetector
    └── TensorRTDetector
```

Similarly:

```text
Tracker
    │
    ├── ByteTrack
    ├── BoTSORT
    └── DeepStreamTracker
```

The event engine should only receive normalized observations.

It should not care which model generated them.

---

# 26. Features We Should NOT Build Initially

Avoid scope explosion.

Do not initially build:

* Full facial recognition database
* Cross-camera person re-identification
* Complex behavioral AI trained from scratch
* VLM analyzing every frame
* Cloud-dependent inference
* 10+ camera support
* Mobile application
* Massive microservice architecture
* Kubernetes
* Complex distributed infrastructure

The prototype should first prove:

```text
ONE CAMERA
    ↓
ONE DETECTOR
    ↓
ONE TRACKER
    ↓
ONE VIRTUAL FENCE
    ↓
ONE RELIABLE ALERT
```

If this works reliably, scale from there.

---

# 27. Milestone Ladder

## M0 – Benchmark

```text
RTX 4050
    ↓
Baseline Model
    ↓
FPS / VRAM / Temperature
```

---

## M1 – Detection

```text
Single Camera
    ↓
Human Detection
```

Success:

* Stable
* No crashes
* No memory leak

---

## M2 – Tracking

```text
Detection
    ↓
Persistent Track IDs
```

---

## M3 – Virtual Fence

```text
Track
    ↓
Boundary Crossing
    ↓
Event
```

---

## M4 – Loitering

```text
Object enters zone
    ↓
Time tracking
    ↓
Loitering event
```

---

## M5 – Event Intelligence

```text
Multiple observations
        ↓
One meaningful incident
```

---

## M6 – Multi-Camera

```text
Camera 1
+
Camera 2
```

Measure:

* FPS
* VRAM
* CPU
* Stability

---

## M7 – ANPR

```text
Vehicle
    ↓
Plate Detection
    ↓
OCR
```

---

## M8 – Night Performance

Benchmark and improve low-light performance.

---

## M9 – TensorRT

```text
PyTorch
    ↓
ONNX
    ↓
TensorRT FP16
```

---

## M10 – DeepStream

Migrate optimized video pipeline if required.

---

## M11 – Command Center

```text
Laptop 1
    ↓
Structured Events
    ↓
Laptop 2
    ↓
Live Dashboard
```

---

## M12 – Competition Build

Feature freeze.

No experimental architecture changes.

No new random models.

No last-minute:

> "Bro, I found this insane GitHub repository at 3 AM."

The final days should focus on:

* Stability
* Demo
* Bug fixing
* Benchmarking
* Presentation

---

# 28. Final SIH Demonstration Story

The demo should be story-driven.

Not:

```text
Feature 1
Feature 2
Feature 3
Feature 4
```

Instead:

# Scenario

Two cameras monitor a simulated border environment.

---

## Camera 1

A person approaches.

System:

```text
PERSON DETECTED
Track ID: 23
```

The person enters a restricted zone.

```text
EVENT:
Restricted Zone Entry
```

The person remains in the area.

```text
EVENT:
Loitering
```

The person crosses the virtual border.

```text
EVENT:
Border Intrusion
```

The system correlates:

```text
Restricted Entry
+
Loitering
+
Border Crossing
+
Night-Time Activity
```

Result:

```text
INCIDENT #014

SEVERITY:
HIGH

RISK SCORE:
87/100
```

---

## Camera 2

A vehicle approaches.

```text
VEHICLE DETECTED
```

The system collects candidate frames.

```text
BEST PLATE FRAME SELECTED
```

Then:

```text
PLATE DETECTED
    ↓
OCR
    ↓
EVENT LOGGED
```

---

## Command Center

Laptop 2 displays:

```text
LIVE CAMERAS

ACTIVE INCIDENTS

MAP

INCIDENT TIMELINE

SYSTEM HEALTH

GPU STATUS

CAMERA STATUS
```

An important feature:

The operator can inspect:

```text
WHY DID THIS ALERT OCCUR?
```

Example:

```text
Risk Score: 87

Contributing Events:

✓ Restricted zone entry
✓ Virtual border crossing
✓ Loitering
✓ Night-time movement
```

This makes the AI system more explainable.

---

# 29. Prototype Workflow Image

A complete infographic was generated showing the system workflow.

The visual architecture includes:

```text
1. Camera Streaming

        ↓

2. Video Ingestion Layer

        ↓

3. Preprocessing & Optimization

        ↓

4. Perception Engine

        ↓

5. Event Engine

        ↓

6. Alert & Notification

        ↓

7. Data Management & Storage

        ↓

8. System Management
```

The image also visually demonstrates:

```text
Original Border Camera Frame
        ↓
Human Detection
        ↓
Pose / Movement Understanding
        ↓
Tracking ID Assignment
        ↓
Virtual Border Line Crossing
        ↓
Illegal Crossing Event
        ↓
Dashboard Alert
```

The intended visual sequence is:

```text
PERSON ATTEMPTS TO CROSS BORDER

Original Frame
        ↓
Human Detected
        ↓
Person Assigned Track ID
        ↓
Trajectory Monitored
        ↓
Virtual Border Crossed
        ↓
Event Triggered
        ↓
Incident Logged
        ↓
Command Center Alert
```

---

# 30. Most Important Technical Risks

Current risk assessment:

| Risk                              | Probability |  Severity |
| --------------------------------- | ----------: | --------: |
| GPU memory pressure               |        High |      High |
| Thermal throttling                |        High |    Medium |
| RTSP instability                  |        High |      High |
| False intrusion alerts            |        High | Very High |
| Tracker ID switches               |        High |      High |
| ANPR reliability                  |      Medium |      High |
| Night detection degradation       |        High |      High |
| TensorRT conversion issues        |      Medium |    Medium |
| DeepStream integration complexity |      Medium |      High |
| Dashboard/network issues          |      Medium |    Medium |
| Dataset/domain mismatch           |        High |      High |
| Licensing issues                  |      Medium |      High |
| Over-engineering                  |   Very High | Very High |

The final item is potentially the biggest threat.

---

# 31. Core Principle: Avoid Over-Engineering

The project already contains enough technical complexity.

The team should resist adding unnecessary features.

The system does not need:

```text
20 AI models
10 microservices
Kubernetes
Cloud infrastructure
Cross-camera ReID
An LLM analyzing every frame
```

The prototype wins by demonstrating:

```text
Reliable Detection
        +
Reliable Tracking
        +
Meaningful Events
        +
Low False Alarms
        +
Efficient Edge Processing
        +
Professional Command Center
```

Reliability is more valuable than a massive feature list.

---

# 32. Final Recommended Architecture

## Development Stage

```text
Python
    +
OpenCV
    +
YOLO-family Detector
    +
ByteTrack / BoT-SORT
    +
Supervision
    +
FastAPI
    +
WebSocket
```

---

## Optimization Stage

```text
PyTorch
    ↓
ONNX
    ↓
TensorRT
    ↓
FP16
```

---

## Production Video Stage

```text
GStreamer
    +
NVIDIA DeepStream
    +
TensorRT
    +
Hardware Video Decode
```

---

## Command Center

```text
React / Next.js
    +
WebSocket
    +
Leaflet
```

---

## Storage

Initially:

```text
SQLite for rapid development
```

Later:

```text
PostgreSQL
```

---

## Deployment

```text
Docker
```

DeepStream deployment should preferably be tested on:

```text
Ubuntu 24.04
```

Laptop 1's RTX 4050 is suitable for TensorRT and DeepStream experimentation.

---

# 33. Immediate Next Action

The first development action should NOT be:

```text
Train a huge model
```

The first action should be:

# Build a reproducible benchmarking environment on Laptop 1.

Goal:

Determine exactly what the RTX 4050 laptop can handle.

Create:

```text
benchmarks/
```

Measure:

```text
Model
Resolution
Backend
FPS
Latency
VRAM
GPU Utilization
CPU Utilization
Temperature
```

Test:

```text
PyTorch FP32
PyTorch FP16
ONNX Runtime
TensorRT FP16
```

Then use actual data to decide:

* Which detector to use
* Which resolution to use
* How many cameras can run
* Whether DeepStream is necessary
* Whether ANPR can run simultaneously
* How much VRAM remains

---

# 34. Ultimate Development Roadmap

```text
┌───────────────────────────────┐
│ PHASE 0                       │
│ Hardware Benchmark            │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ PHASE 1                       │
│ Single Camera Detection       │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ PHASE 2                       │
│ Multi-Object Tracking         │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ PHASE 3                       │
│ Virtual Fence + Events        │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ PHASE 4                       │
│ Risk + Incident Intelligence  │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ PHASE 5                       │
│ Vehicle + ANPR                │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ PHASE 6                       │
│ Night Performance             │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ PHASE 7                       │
│ TensorRT Optimization         │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ PHASE 8                       │
│ DeepStream / GStreamer        │
│ if required                   │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ PHASE 9                       │
│ Command Center                │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ PHASE 10                      │
│ Hardening & Bug Testing       │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ PHASE 11                      │
│ Competition Demo Build        │
└───────────────────────────────┘
```

---

# 35. Final Strategic Conclusion

The project is technically ambitious but feasible.

The available RTX 4050 laptop is sufficient for a strong prototype if the architecture is designed intelligently.

The project is not blocked by:

* Lack of AI models
* Lack of datasets
* Lack of workstation-class hardware
* Lack of open-source tools

The real engineering challenge is:

```text
REAL-TIME VIDEO
        +
RESOURCE CONSTRAINTS
        +
LOW FALSE ALARMS
        +
STABLE TRACKING
        +
EVENT INTELLIGENCE
        +
RELIABLE DEMO
```

The intended path is:

```text
START SIMPLE

Python + OpenCV
        ↓

PROVE THE CORE SYSTEM

Detection + Tracking + Events
        ↓

BUILD INTELLIGENCE

Risk + Incident Correlation
        ↓

OPTIMIZE

ONNX + FP16 + TensorRT
        ↓

SCALE VIDEO PIPELINE

GStreamer + DeepStream
        ↓

HARDEN

RTSP Recovery
Metrics
Thermal Testing
Error Handling
        ↓

COMMAND CENTER

Laptop 1 → Laptop 2
        ↓

SIH DEMO BUILD
```

---

# 36. Golden Rules for the Project

## Rule 1

Do not optimize before measuring.

---

## Rule 2

Do not add AI where geometry and rules are sufficient.

---

## Rule 3

Detection is not an incident.

---

## Rule 4

Do not process every frame if it provides no additional value.

---

## Rule 5

Current frames are more valuable than an infinitely growing queue of stale frames.

---

## Rule 6

False positives can damage the prototype more than slightly lower detection accuracy.

---

## Rule 7

Build the simplest possible working pipeline first.

```text
One Camera
One Detector
One Tracker
One Virtual Fence
One Alert
```

---

## Rule 8

Every feature added must answer:

> Does this improve the actual border surveillance demonstration?

If not, do not add it.

---

## Rule 9

Benchmark sustained performance, not 30-second benchmark performance.

---

## Rule 10

Before the competition:

```text
FEATURE FREEZE
```

No random repositories.

No new architecture.

No experimental model added at midnight.

Focus on:

```text
Stability
Performance
Demo
Presentation
Bug Fixes
```

---

# End of Context

This document represents the current technical and strategic context for developing the SIH26187 prototype.
Future work should treat this as the baseline architecture and modify it only when supported by benchmarking, testing, or a clear improvement to the competition prototype.


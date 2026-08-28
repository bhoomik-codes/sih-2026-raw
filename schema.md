# IBVAP Database Schema Specification

**Project:** IBVAP, Intelligent Border Video Analytics Platform
**SIH Problem:** SIH26187
**Database target:** SQLite for prototype → PostgreSQL for production
**Schema version:** `v1.0`

This schema is derived from the current project architecture and README files. The project already defines persistent storage for incidents, observations, timeline data, camera metadata, risk scores, and timestamps, while the dashboard requires camera status, incidents, zones/fences, alerts, and system-health data.  

```text
CAMERA CONFIGURATION
        │
        ├── Camera Zones / Fences
        │
        └── Camera Health
                │
                ▼
VIDEO
  │
  ▼
TRACKS
  │
  ▼
OBSERVATIONS
  │
  ▼
EVENTS
  │
  ▼
INCIDENTS
  │
  ├── Incident Events
  ├── Evidence
  └── Operator Actions

SYSTEM
  ├── Nodes
  ├── Health Metrics
  └── Logs
```

---

# 1. Database Design Principles

## 1.1 Separate raw observations from actual incidents

This is probably the most important database decision.

A person being detected is an **observation**.

A person crossing a virtual fence is an **event**.

A correlated sequence of suspicious events becomes an **incident**.

```text
Detection
   ↓
Observation
   ↓
Event
   ↓
Correlation
   ↓
Incident
```

The project's architecture explicitly states:

> Detection ≠ Incident

and requires temporal confirmation to reduce false positives. 

Therefore:

```text
observations ≠ events ≠ incidents
```

---

# 2. Complete Schema

I recommend the following **16 core tables**:

| #  | Table              | Purpose                            | Priority       |
| -- | ------------------ | ---------------------------------- | -------------- |
| 1  | `cameras`          | Camera configuration + connection  | 🔴 Essential   |
| 2  | `camera_streams`   | Stream endpoints/configuration     | 🔴 Essential   |
| 3  | `zones`            | Restricted/safe/warning areas      | 🔴 Essential   |
| 4  | `zone_points`      | Polygon/fence geometry             | 🔴 Essential   |
| 5  | `detection_tracks` | Persistent tracked objects         | 🔴 Essential   |
| 6  | `observations`     | Object observations                | 🔴 Essential   |
| 7  | `events`           | Detected behavioural/system events | 🔴 Essential   |
| 8  | `incidents`        | Correlated security incidents      | 🔴 Essential   |
| 9  | `incident_events`  | Event → incident relationship      | 🔴 Essential   |
| 10 | `evidence`         | Images/video/evidence references   | 🟠 Important   |
| 11 | `anpr_results`     | Vehicle/plate recognition          | 🟠 Important   |
| 12 | `rules`            | Event/risk rules                   | 🟠 Important   |
| 13 | `camera_health`    | Camera runtime health              | 🟠 Important   |
| 14 | `system_metrics`   | GPU/CPU/FPS/etc.                   | 🟠 Important   |
| 15 | `system_logs`      | Application/system logs            | 🔴 Essential   |
| 16 | `audit_logs`       | Operator/admin actions             | 🟡 Recommended |

---

# 3. Entity Relationship Diagram

```text
                              ┌──────────────┐
                              │   cameras    │
                              └──────┬───────┘
                                     │
                 ┌───────────────────┼──────────────────┐
                 │                   │                  │
                 ▼                   ▼                  ▼
        ┌────────────────┐   ┌──────────────┐   ┌───────────────┐
        │camera_streams  │   │    zones     │   │camera_health  │
        └────────────────┘   └──────┬───────┘   └───────────────┘
                                    │
                                    ▼
                             ┌──────────────┐
                             │ zone_points  │
                             └──────────────┘

        CAMERA
          │
          ▼
 ┌──────────────────┐
 │ detection_tracks │
 └────────┬─────────┘
          │
          ▼
 ┌──────────────────┐
 │   observations   │
 └────────┬─────────┘
          │
          ▼
 ┌──────────────────┐
 │      events      │◄────────────── rules
 └────────┬─────────┘
          │
          │ many-to-many
          ▼
 ┌──────────────────┐
 │ incident_events  │
 └────────┬─────────┘
          │
          ▼
 ┌──────────────────┐
 │    incidents     │
 └───────┬──────────┘
         │
         ▼
 ┌──────────────────┐
 │     evidence     │
 └──────────────────┘


 SYSTEM
   │
   ├── system_metrics
   ├── system_logs
   └── audit_logs
```

---

# 4. `cameras`

## Purpose

The **central camera registry**.

This should contain everything required to identify and configure a camera, but I recommend separating the actual connection endpoints into `camera_streams`.

The camera requirements originate directly from the planned dashboard functionality: add/configure cameras, display status, enable/disable cameras, and associate cameras with locations. 

## Schema

```sql
CREATE TABLE cameras (
    id                  TEXT PRIMARY KEY,

    camera_code         TEXT NOT NULL UNIQUE,
    name                TEXT NOT NULL,

    description         TEXT,

    source_type         TEXT NOT NULL,
    -- rtsp, http, mjpeg, webcam, file, smartphone

    manufacturer        TEXT,
    model               TEXT,
    serial_number       TEXT,

    location_name       TEXT,
    latitude            REAL,
    longitude           REAL,

    enabled             INTEGER NOT NULL DEFAULT 1,

    status              TEXT NOT NULL DEFAULT 'UNKNOWN',
    -- ONLINE, OFFLINE, DEGRADED, UNKNOWN

    last_seen_at        TIMESTAMP,
    created_at          TIMESTAMP NOT NULL,
    updated_at          TIMESTAMP NOT NULL
);
```

### Example

```text
id:
cam_01

camera_code:
BOP-CAM-01

name:
East Border Fence

source_type:
rtsp

location_name:
BOP East

status:
ONLINE
```

---

# 5. `camera_streams`

This is where your **camera connection strings** belong.

I strongly recommend **not** putting the password directly into the general `cameras` table.

## Schema

```sql
CREATE TABLE camera_streams (
    id                  TEXT PRIMARY KEY,

    camera_id           TEXT NOT NULL,

    stream_name         TEXT NOT NULL,

    protocol            TEXT NOT NULL,
    -- RTSP, HTTP, MJPEG, TCP, UDP

    connection_string   TEXT NOT NULL,

    username            TEXT,

    password_encrypted  TEXT,

    stream_role         TEXT NOT NULL DEFAULT 'primary',
    -- primary, secondary, snapshot

    resolution_width    INTEGER,
    resolution_height   INTEGER,

    source_fps          REAL,

    enabled             INTEGER NOT NULL DEFAULT 1,

    connection_timeout_ms INTEGER DEFAULT 5000,
    reconnect_enabled   INTEGER NOT NULL DEFAULT 1,
    reconnect_attempts  INTEGER DEFAULT 5,

    created_at          TIMESTAMP NOT NULL,
    updated_at          TIMESTAMP NOT NULL,

    FOREIGN KEY (camera_id)
        REFERENCES cameras(id)
        ON DELETE CASCADE
);
```

---

# 6. Connection String Design

Example:

```text
rtsp://192.168.1.50:554/stream1
```

or:

```text
rtsp://username:password@192.168.1.50:554/stream1
```

But **do not store the second form in plaintext**.

Prefer:

```text
connection_string:
rtsp://192.168.1.50:554/stream1

username:
admin

password_encrypted:
<encrypted value>
```

Then the application constructs the authenticated connection at runtime.

### Why?

The database will eventually contain highly sensitive infrastructure information.

The mobile dashboard should **never receive raw credentials**.

---

# 7. Smartphone Camera Records

A smartphone can simply appear as:

```text
cameras.source_type = "smartphone"
```

Example:

```sql
INSERT INTO cameras (
    id,
    camera_code,
    name,
    source_type,
    status,
    enabled,
    created_at,
    updated_at
)
VALUES (
    'cam_phone_01',
    'PHONE-CAM-01',
    'Mobile Border Camera',
    'smartphone',
    'ONLINE',
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);
```

Its stream can then be:

```text
http://192.168.1.20:8080/video
```

or an RTSP endpoint.

This keeps the rest of IBVAP completely unaware that the camera happens to be a phone.

---

# 8. `zones`

This represents a logical surveillance region.

Examples:

```text
SAFE
WARNING
RESTRICTED
CHECKPOINT
BORDER
VEHICLE_ONLY
```

## Schema

```sql
CREATE TABLE zones (
    id                  TEXT PRIMARY KEY,

    camera_id           TEXT NOT NULL,

    name                TEXT NOT NULL,

    zone_type           TEXT NOT NULL,
    -- safe, warning, restricted,
    -- checkpoint, border, vehicle_only

    description         TEXT,

    enabled             INTEGER NOT NULL DEFAULT 1,

    severity_weight     INTEGER DEFAULT 0,

    created_at          TIMESTAMP NOT NULL,
    updated_at          TIMESTAMP NOT NULL,

    FOREIGN KEY (camera_id)
        REFERENCES cameras(id)
        ON DELETE CASCADE
);
```

---

# 9. `zone_points`

Do **not** store a polygon as an opaque string if you expect to manipulate it frequently.

Store the points separately.

```sql
CREATE TABLE zone_points (
    id              TEXT PRIMARY KEY,

    zone_id         TEXT NOT NULL,

    point_index     INTEGER NOT NULL,

    x               REAL NOT NULL,
    y               REAL NOT NULL,

    FOREIGN KEY (zone_id)
        REFERENCES zones(id)
        ON DELETE CASCADE,

    UNIQUE(zone_id, point_index)
);
```

Example:

```text
ZONE-01

point 0 → (100, 100)
point 1 → (500, 100)
point 2 → (600, 400)
point 3 → (100, 400)
```

This works for both:

```text
Polygon
```

and:

```text
Virtual Fence
```

A fence can simply be a zone with:

```text
zone_type = "restricted"
```

or a dedicated rule referencing its geometry.

---

# 10. `detection_tracks`

This table represents the lifecycle of a tracked object.

The tracker should maintain persistent IDs rather than treating every detection as a new object.

## Schema

```sql
CREATE TABLE detection_tracks (
    id                  TEXT PRIMARY KEY,

    camera_id           TEXT NOT NULL,

    tracker_id          INTEGER NOT NULL,

    object_class        TEXT NOT NULL,
    -- person, car, motorcycle, truck, etc.

    first_seen_at       TIMESTAMP NOT NULL,
    last_seen_at        TIMESTAMP NOT NULL,

    first_frame_ts      TIMESTAMP,
    last_frame_ts       TIMESTAMP,

    confidence_avg      REAL,

    status              TEXT NOT NULL DEFAULT 'ACTIVE',
    -- ACTIVE, LOST, CLOSED

    observation_count   INTEGER DEFAULT 0,

    created_at          TIMESTAMP NOT NULL,

    FOREIGN KEY (camera_id)
        REFERENCES cameras(id)
);
```

### Why separate this from observations?

Because:

```text
Track #42
```

may generate:

```text
Observation 1
Observation 2
Observation 3
...
Observation 200
```

The track represents the **entity over time**.

The observations represent its individual appearances.

---

# 11. `observations`

This stores object-level observations.

## Schema

```sql
CREATE TABLE observations (
    id                  TEXT PRIMARY KEY,

    camera_id           TEXT NOT NULL,
    track_id            TEXT,

    capture_ts          TIMESTAMP NOT NULL,
    ingest_ts           TIMESTAMP NOT NULL,

    object_class        TEXT NOT NULL,

    confidence          REAL,

    bbox_x1             REAL NOT NULL,
    bbox_y1             REAL NOT NULL,
    bbox_x2             REAL NOT NULL,
    bbox_y2             REAL NOT NULL,

    center_x            REAL,
    center_y            REAL,

    zone_id             TEXT,

    frame_number        INTEGER,

    inference_model     TEXT,

    inference_backend   TEXT,

    created_at          TIMESTAMP NOT NULL,

    FOREIGN KEY (camera_id)
        REFERENCES cameras(id),

    FOREIGN KEY (track_id)
        REFERENCES detection_tracks(id),

    FOREIGN KEY (zone_id)
        REFERENCES zones(id)
);
```

---

# 12. Why `capture_ts` and `ingest_ts`?

The project explicitly identifies the **three clocks problem**:

```text
Camera Clock
Processing Clock
Dashboard Clock
```

and recommends retaining separate timestamps. 

For database design:

```text
capture_ts
↓
Camera/frame timestamp

ingest_ts
↓
Edge processing timestamp

event_ts
↓
When event was logically generated

display_ts
↓
When dashboard received it
```

We should preserve all four where relevant.

---

# 13. `events`

This is the **core intelligence table**.

An event is something meaningful that happened.

Examples:

```text
zone_entry
zone_exit
virtual_fence_crossing
loitering
night_movement
vehicle_detected
person_detected
anpr_detected
camera_offline
```

## Schema

```sql
CREATE TABLE events (
    id                  TEXT PRIMARY KEY,

    event_code          TEXT NOT NULL UNIQUE,

    camera_id           TEXT NOT NULL,

    track_id            TEXT,

    zone_id             TEXT,

    event_type          TEXT NOT NULL,

    severity            TEXT NOT NULL DEFAULT 'LOW',
    -- LOW, MEDIUM, HIGH, CRITICAL

    risk_score          REAL DEFAULT 0,

    confidence          REAL,

    capture_ts          TIMESTAMP,
    ingest_ts           TIMESTAMP NOT NULL,
    event_ts            TIMESTAMP NOT NULL,
    display_ts          TIMESTAMP,

    bbox_x1             REAL,
    bbox_y1             REAL,
    bbox_x2             REAL,
    bbox_y2             REAL,

    status              TEXT NOT NULL DEFAULT 'ACTIVE',
    -- ACTIVE, CONFIRMED, DISMISSED, RESOLVED

    description         TEXT,

    metadata_json       TEXT,

    created_at          TIMESTAMP NOT NULL,

    FOREIGN KEY (camera_id)
        REFERENCES cameras(id),

    FOREIGN KEY (track_id)
        REFERENCES detection_tracks(id),

    FOREIGN KEY (zone_id)
        REFERENCES zones(id)
);
```

The project's existing draft event schema contains `event_id`, `camera_id`, `event_type`, `track_id`, `risk_score`, `severity`, contributing events, timestamps, and bounding box information. 

---

# 14. Example Event

```json
{
  "id": "evt_000142",

  "event_code": "EVT-000142",

  "camera_id": "BOP-CAM-01",

  "track_id": "track_23",

  "zone_id": "zone_restricted_01",

  "event_type": "virtual_fence_crossing",

  "severity": "HIGH",

  "risk_score": 72,

  "capture_ts": "2026-08-27T18:20:00Z",

  "ingest_ts": "2026-08-27T18:20:00.180Z",

  "event_ts": "2026-08-27T18:20:00.210Z",

  "display_ts": null,

  "bbox": [120, 80, 280, 420],

  "status": "CONFIRMED"
}
```

---

# 15. `incidents`

This is **not another event table**.

An incident is a higher-level security situation.

Example:

```text
Person detected
       +
Restricted zone entry
       +
Loitering
       +
Fence crossing
       ↓
INCIDENT
```

## Schema

```sql
CREATE TABLE incidents (
    id                  TEXT PRIMARY KEY,

    incident_code       TEXT NOT NULL UNIQUE,

    camera_id           TEXT NOT NULL,

    track_id            TEXT,

    incident_type       TEXT NOT NULL,

    severity            TEXT NOT NULL,

    risk_score          REAL NOT NULL DEFAULT 0,

    status              TEXT NOT NULL DEFAULT 'OPEN',
    -- OPEN
    -- ACKNOWLEDGED
    -- RESOLVED
    -- FALSE_POSITIVE
    -- DISMISSED

    title               TEXT NOT NULL,

    description         TEXT,

    first_event_ts      TIMESTAMP,
    last_event_ts       TIMESTAMP,

    created_at          TIMESTAMP NOT NULL,
    updated_at          TIMESTAMP NOT NULL,

    acknowledged_at     TIMESTAMP,
    resolved_at         TIMESTAMP,

    acknowledged_by     TEXT,
    resolved_by         TEXT,

    FOREIGN KEY (camera_id)
        REFERENCES cameras(id),

    FOREIGN KEY (track_id)
        REFERENCES detection_tracks(id)
);
```

---

# 16. `incident_events`

An incident can contain multiple events.

Therefore:

```text
Incident
   ↕
Many Events
```

Use a junction table.

```sql
CREATE TABLE incident_events (
    incident_id         TEXT NOT NULL,
    event_id            TEXT NOT NULL,

    contribution_score  REAL DEFAULT 0,

    is_primary          INTEGER DEFAULT 0,

    created_at          TIMESTAMP NOT NULL,

    PRIMARY KEY (incident_id, event_id),

    FOREIGN KEY (incident_id)
        REFERENCES incidents(id)
        ON DELETE CASCADE,

    FOREIGN KEY (event_id)
        REFERENCES events(id)
        ON DELETE CASCADE
);
```

---

# 17. Explainability

This table allows the dashboard to display:

```text
WHY DID THIS ALERT FIRE?

✓ Restricted zone entry       +20
✓ Fence crossing              +35
✓ Loitering                   +15
✓ Night activity              +25

TOTAL                         95
```

Instead of storing:

```text
"reason": "AI thinks suspicious"
```

you can derive the explanation from `incident_events`.

That is much more defensible.

---

# 18. `rules`

Rules determine how observations become events.

## Schema

```sql
CREATE TABLE rules (
    id                  TEXT PRIMARY KEY,

    name                TEXT NOT NULL,

    rule_type           TEXT NOT NULL,

    description         TEXT,

    enabled             INTEGER NOT NULL DEFAULT 1,

    priority            INTEGER DEFAULT 0,

    threshold_value     REAL,

    threshold_unit      TEXT,

    cooldown_seconds    INTEGER DEFAULT 0,

    risk_weight         REAL DEFAULT 0,

    severity             TEXT DEFAULT 'MEDIUM',

    configuration_json  TEXT,

    created_at          TIMESTAMP NOT NULL,
    updated_at          TIMESTAMP NOT NULL
);
```

Examples:

```text
loitering
zone_entry
fence_crossing
night_movement
direction_violation
```

---

# 19. Example Rule

```json
{
  "name": "Restricted Zone Loitering",

  "rule_type": "loitering",

  "enabled": true,

  "threshold_value": 30,

  "threshold_unit": "seconds",

  "cooldown_seconds": 60,

  "risk_weight": 20
}
```

This means:

```text
Person enters restricted zone
        ↓
Stays > 30 sec
        ↓
Loitering Event
```

---

# 20. `evidence`

Do not put large images or videos directly inside the database.

Store the **path/reference**.

## Schema

```sql
CREATE TABLE evidence (
    id                  TEXT PRIMARY KEY,

    incident_id         TEXT,
    event_id            TEXT,

    camera_id           TEXT NOT NULL,

    evidence_type       TEXT NOT NULL,
    -- snapshot
    -- video_clip
    -- plate_crop
    -- face_crop
    -- frame

    storage_path        TEXT NOT NULL,

    filename            TEXT,

    mime_type           TEXT,

    file_size_bytes     INTEGER,

    capture_ts          TIMESTAMP,

    hash_sha256         TEXT,

    metadata_json       TEXT,

    created_at          TIMESTAMP NOT NULL,

    FOREIGN KEY (incident_id)
        REFERENCES incidents(id)
        ON DELETE CASCADE,

    FOREIGN KEY (event_id)
        REFERENCES events(id)
        ON DELETE CASCADE,

    FOREIGN KEY (camera_id)
        REFERENCES cameras(id)
);
```

Example:

```text
evidence_type:
snapshot

storage_path:
/data/evidence/2026/08/27/INC-000142/frame_001.jpg
```

---

# 21. `anpr_results`

ANPR should be **event-triggered**, not continuously executed.

The current architecture explicitly proposes:

```text
Vehicle enters checkpoint
        ↓
Collect candidate frames
        ↓
Select best frame
        ↓
Plate detection
        ↓
OCR
```

rather than OCR on every frame. 

## Schema

```sql
CREATE TABLE anpr_results (
    id                  TEXT PRIMARY KEY,

    camera_id           TEXT NOT NULL,

    track_id            TEXT,

    event_id            TEXT,

    vehicle_class       TEXT,

    plate_text          TEXT,

    normalized_plate    TEXT,

    detection_confidence REAL,

    ocr_confidence      REAL,

    plate_bbox_x1       REAL,
    plate_bbox_y1       REAL,
    plate_bbox_x2       REAL,
    plate_bbox_y2       REAL,

    capture_ts          TIMESTAMP,

    evidence_id         TEXT,

    validation_status   TEXT DEFAULT 'UNVERIFIED',

    created_at          TIMESTAMP NOT NULL,

    FOREIGN KEY (camera_id)
        REFERENCES cameras(id),

    FOREIGN KEY (track_id)
        REFERENCES detection_tracks(id),

    FOREIGN KEY (event_id)
        REFERENCES events(id),

    FOREIGN KEY (evidence_id)
        REFERENCES evidence(id)
);
```

---

# 22. Important ANPR Design Decision

Store:

```text
plate detection confidence
```

and:

```text
OCR confidence
```

separately.

The existing project specifically says not to conflate plate detection accuracy with OCR exact-match accuracy. 

So don't create:

```text
anpr_accuracy = 97%
```

Instead:

```text
plate_detection_confidence = 0.94
ocr_confidence = 0.82
```

---

# 23. `camera_health`

This stores camera connectivity information.

The dashboard needs per-camera FPS, status, dropped frames, and edge-node connection status. 

## Schema

```sql
CREATE TABLE camera_health (
    id                  TEXT PRIMARY KEY,

    camera_id           TEXT NOT NULL,

    timestamp           TIMESTAMP NOT NULL,

    status              TEXT NOT NULL,

    fps                 REAL,

    latency_ms          REAL,

    dropped_frames      INTEGER DEFAULT 0,

    dropped_frame_rate  REAL,

    queue_depth         INTEGER,

    decode_errors       INTEGER DEFAULT 0,

    reconnect_count     INTEGER DEFAULT 0,

    last_frame_at       TIMESTAMP,

    stream_resolution   TEXT,

    error_message       TEXT,

    FOREIGN KEY (camera_id)
        REFERENCES cameras(id)
        ON DELETE CASCADE
);
```

---

# 24. Health Metrics

You should **not update the same camera-health row forever**.

Create periodic measurements.

For example:

```text
10:00:00 → 11.7 FPS
10:00:05 → 11.9 FPS
10:00:10 → 11.5 FPS
```

This allows the dashboard to graph performance.

---

# 25. `system_metrics`

This handles Laptop 1's AI/edge performance.

The project explicitly identifies:

* FPS
* inference latency
* queue depth
* dropped frames
* GPU utilization
* VRAM
* CPU
* RAM
* GPU temperature

as important observability metrics. 

## Schema

```sql
CREATE TABLE system_metrics (
    id                  TEXT PRIMARY KEY,

    node_id             TEXT NOT NULL,

    timestamp           TIMESTAMP NOT NULL,

    cpu_percent         REAL,

    ram_percent         REAL,
    ram_used_mb         REAL,

    gpu_utilization     REAL,

    gpu_memory_used_mb  REAL,
    gpu_memory_total_mb REAL,

    gpu_temperature_c   REAL,

    inference_fps       REAL,

    inference_latency_ms REAL,

    queue_depth         INTEGER,

    dropped_frames      INTEGER,

    active_cameras      INTEGER,

    detector_status     TEXT,

    tracker_status      TEXT,

    backend_status      TEXT
);
```

---

# 26. `nodes`

Because eventually you have:

```text
Laptop 1
Laptop 2
```

and potentially:

```text
another edge machine
```

you should identify them.

## Schema

```sql
CREATE TABLE nodes (
    id                  TEXT PRIMARY KEY,

    node_code           TEXT NOT NULL UNIQUE,

    name                TEXT NOT NULL,

    node_type           TEXT NOT NULL,
    -- edge, backend, dashboard

    hostname            TEXT,

    ip_address          TEXT,

    operating_system    TEXT,

    cpu_model           TEXT,

    gpu_model           TEXT,

    gpu_vram_mb         INTEGER,

    status              TEXT DEFAULT 'ONLINE',

    last_heartbeat_at   TIMESTAMP,

    created_at          TIMESTAMP NOT NULL,
    updated_at          TIMESTAMP NOT NULL
);
```

Example:

```text
EDGE-01
AI Edge Node
RTX 4050
6 GB VRAM
```

and:

```text
CMD-01
Command Center
Intel Iris Xe
```

---

# 27. `system_logs`

You specifically asked for a logs table.

This is different from an event.

### Event

Something happened in the surveillance domain.

```text
Person crossed fence
```

### Log

Something happened inside the software.

```text
RTSP connection failed
```

The project already identifies RTSP failures, GPU failures, tracking failures, backend WebSocket failures, database locking, and dashboard synchronization problems as things that need monitoring. 

## Schema

```sql
CREATE TABLE system_logs (
    id                  TEXT PRIMARY KEY,

    timestamp           TIMESTAMP NOT NULL,

    node_id             TEXT,

    component           TEXT NOT NULL,

    level               TEXT NOT NULL,
    -- DEBUG
    -- INFO
    -- WARNING
    -- ERROR
    -- CRITICAL

    category            TEXT,
    -- video
    camera
    -- detection
    -- tracking
    -- intelligence
    -- backend
    -- database
    -- gpu
    -- dashboard
    -- deployment

    message             TEXT NOT NULL,

    exception_type      TEXT,

    stack_trace         TEXT,

    camera_id           TEXT,

    event_id            TEXT,

    incident_id         TEXT,

    metadata_json       TEXT,

    FOREIGN KEY (node_id)
        REFERENCES nodes(id),

    FOREIGN KEY (camera_id)
        REFERENCES cameras(id),

    FOREIGN KEY (event_id)
        REFERENCES events(id),

    FOREIGN KEY (incident_id)
        REFERENCES incidents(id)
);
```

---

# 28. Example System Logs

### Camera failure

```json
{
  "level": "ERROR",
  "component": "RTSPClient",
  "category": "camera",
  "camera_id": "BOP-CAM-01",
  "message": "RTSP stream disconnected"
}
```

### Automatic recovery

```json
{
  "level": "INFO",
  "component": "RTSPWatchdog",
  "category": "camera",
  "camera_id": "BOP-CAM-01",
  "message": "Stream successfully reconnected"
}
```

### GPU warning

```json
{
  "level": "WARNING",
  "component": "InferenceEngine",
  "category": "gpu",
  "message": "VRAM usage exceeded configured threshold"
}
```

---

# 29. `audit_logs`

This is for **human/operator actions**, not machine logs.

Example:

```text
Operator changed fence
Operator acknowledged incident
Operator disabled camera
Operator changed risk threshold
```

## Schema

```sql
CREATE TABLE audit_logs (
    id                  TEXT PRIMARY KEY,

    timestamp           TIMESTAMP NOT NULL,

    actor_id            TEXT,

    action              TEXT NOT NULL,

    entity_type         TEXT NOT NULL,

    entity_id           TEXT,

    old_value_json      TEXT,

    new_value_json      TEXT,

    source_ip            TEXT,

    client_type         TEXT,
    -- desktop, mobile, api

    description         TEXT
);
```

This becomes especially useful once multiple operators can access the system.

---

# 30. Recommended Indexes

The database will become much faster with deliberate indexes.

```sql
CREATE INDEX idx_cameras_status
ON cameras(status);

CREATE INDEX idx_streams_camera
ON camera_streams(camera_id);

CREATE INDEX idx_zones_camera
ON zones(camera_id);

CREATE INDEX idx_tracks_camera
ON detection_tracks(camera_id);

CREATE INDEX idx_observations_camera_time
ON observations(camera_id, capture_ts);

CREATE INDEX idx_observations_track
ON observations(track_id);

CREATE INDEX idx_events_camera_time
ON events(camera_id, event_ts);

CREATE INDEX idx_events_type
ON events(event_type);

CREATE INDEX idx_events_severity
ON events(severity);

CREATE INDEX idx_events_status
ON events(status);

CREATE INDEX idx_incidents_camera
ON incidents(camera_id);

CREATE INDEX idx_incidents_status
ON incidents(status);

CREATE INDEX idx_incidents_time
ON incidents(created_at);

CREATE INDEX idx_incidents_severity
ON incidents(severity);

CREATE INDEX idx_health_camera_time
ON camera_health(camera_id, timestamp);

CREATE INDEX idx_metrics_node_time
ON system_metrics(node_id, timestamp);

CREATE INDEX idx_logs_timestamp
ON system_logs(timestamp);

CREATE INDEX idx_logs_level
ON system_logs(level);

CREATE INDEX idx_logs_component
ON system_logs(component);
```

---

# 31. Database Relationship Example

Suppose:

```text
CAM-01
```

sees:

```text
Person #23
```

The database becomes:

```text
cameras
─────────────
CAM-01
   │
   ▼
detection_tracks
─────────────
track_23
person
   │
   ├───────────────┐
   ▼               ▼
observations       events
─────────────      ───────────────
obs_1              zone_entry
obs_2              loitering
obs_3              fence_crossing
obs_4                    │
                          │
                          ▼
                  incident_events
                          │
                          ▼
                     incidents
                  ───────────────
                  INC-000142
                  risk = 87
                  severity = HIGH
```

That gives you a clean causal chain.

---

# 32. Full Incident Example

Imagine someone enters a restricted zone at night.

### Step 1

Detector sees:

```text
Person
confidence = 0.91
```

Create:

```text
observation
```

---

### Step 2

Tracker assigns:

```text
track_id = 42
```

Create/update:

```text
detection_tracks
```

---

### Step 3

Person enters restricted zone.

Create:

```text
event:
ZONE_ENTRY
risk = +20
```

---

### Step 4

Person remains for 40 seconds.

Create:

```text
event:
LOITERING
risk = +15
```

---

### Step 5

Person crosses virtual fence.

Create:

```text
event:
VIRTUAL_FENCE_CROSSING
risk = +35
```

---

### Step 6

Night activity rule triggers.

```text
event:
NIGHT_MOVEMENT
risk = +25
```

---

### Step 7

Risk engine correlates them.

```text
20 + 15 + 35 + 25
= 95
```

Create:

```text
incident:
INC-000142

risk_score:
95

severity:
CRITICAL
```

---

# 33. Dashboard Query Model

This schema also maps very cleanly onto the dashboard.

## Active Incidents

```sql
SELECT *
FROM incidents
WHERE status IN ('OPEN', 'ACKNOWLEDGED')
ORDER BY risk_score DESC;
```

---

## Camera Status

```sql
SELECT
    camera_code,
    name,
    status,
    last_seen_at
FROM cameras
ORDER BY camera_code;
```

---

## Incident Explanation

```sql
SELECT
    e.event_type,
    e.risk_score,
    e.severity,
    e.event_ts
FROM incident_events ie
JOIN events e
    ON e.id = ie.event_id
WHERE ie.incident_id = 'INC-000142'
ORDER BY e.event_ts;
```

---

# 34. Mobile Dashboard Query

The smartphone dashboard should receive **only the information it needs**.

Example API:

```http
GET /api/mobile/summary
```

Response:

```json
{
  "system_status": "ONLINE",

  "active_incidents": 2,

  "highest_risk": {
    "incident_id": "INC-000142",
    "camera": "BOP-CAM-01",
    "risk_score": 95,
    "severity": "CRITICAL"
  },

  "cameras": {
    "online": 3,
    "offline": 1
  }
}
```

Do **not** send:

```text
camera password
RTSP connection string
internal filesystem paths
raw system logs
```

to the phone.

---

# 35. What Should NOT Be Stored in the Database

Avoid turning the database into a video warehouse.

## Don't store

```text
Every raw video frame
```

or:

```text
Every 30 FPS JPEG
```

That will explode storage.

The project already emphasizes dropping stale frames and not processing every frame. 

Instead store:

```text
Observations
Events
Incidents
Selected evidence
Metrics
Logs
```

and optionally short evidence clips.

---

# 36. Retention Strategy

I recommend:

| Data           |    Retention |
| -------------- | -----------: |
| Cameras        |    Permanent |
| Zones          |    Permanent |
| Rules          |    Permanent |
| Incidents      |    Long-term |
| Events         |   30-90 days |
| Observations   |     1-7 days |
| Camera health  |    7-30 days |
| System metrics |    7-30 days |
| Logs           |    7-30 days |
| Evidence       | Configurable |

For the SIH prototype, you can simply retain everything locally.

For a production deployment, retention should become configurable.

---

# 37. SQLite vs PostgreSQL

The project's backend README already proposes:

```text
SQLite → development
PostgreSQL → production
```

with SQLAlchemy as the database abstraction. 

I agree with that.

## Prototype

```text
FastAPI
   ↓
SQLAlchemy
   ↓
SQLite
```

Advantages:

* zero database server
* easy SIH deployment
* one file
* easy backup
* excellent for your current scale

## Later

```text
FastAPI
   ↓
SQLAlchemy
   ↓
PostgreSQL
```

when you need:

* multiple edge nodes
* multiple command centers
* concurrent operators
* larger event volumes
* stronger database concurrency

---

# 38. SQLite JSON Strategy

Because SQLite does not have PostgreSQL's native `JSONB`, use:

```sql
metadata_json TEXT
```

and store:

```json
{
  "direction": "north",
  "duration": 42,
  "model": "yolov8n",
  "confidence": 0.92
}
```

SQLAlchemy can later map this to PostgreSQL JSON/JSONB.

This keeps the prototype portable.

---

# 39. Recommended ID Strategy

Use application-generated IDs rather than database auto-increment IDs.

For example:

```text
cam_01a8...
track_01a8...
obs_01a8...
evt_01a8...
inc_01a8...
```

and human-readable codes:

```text
BOP-CAM-01
EVT-000142
INC-000142
```

Therefore:

```text
internal ID
+
human-readable code
```

Example:

```text
id:
01990f7e-...

incident_code:
INC-000142
```

---

# 40. Security Requirements for the Database

This deserves special attention because you are storing camera credentials.

## Connection strings

**Never expose them through:**

```text
GET /cameras
```

Instead API response:

```json
{
  "id": "cam_01",
  "name": "East Border",
  "source_type": "rtsp",
  "status": "ONLINE"
}
```

Not:

```json
{
  "connection_string":
  "rtsp://admin:password@192.168.1.50/..."
}
```

## Better architecture

```text
Database
   │
   │ encrypted credential
   ▼
Backend
   │
   │ actual RTSP credential
   ▼
Edge pipeline
```

The dashboard only knows:

```text
CAM-01
ONLINE
```

---

# 41. Database-Level State Machine

For cameras:

```text
UNKNOWN
   ↓
CONNECTING
   ↓
ONLINE
   │
   ├── connection failure
   ▼
DEGRADED
   │
   ▼
OFFLINE
   │
   ▼
RECONNECTING
   │
   ▼
ONLINE
```

For incidents:

```text
OPEN
 ↓
ACKNOWLEDGED
 ↓
RESOLVED
```

Alternative:

```text
OPEN
 ↓
FALSE_POSITIVE
```

This prevents random string values from appearing throughout the codebase.

---

# 42. What I Would Implement First

Do **not** implement all 16 tables on day one.

### Database MVP

```text
1. cameras
2. camera_streams
3. zones
4. zone_points
5. detection_tracks
6. observations
7. events
8. incidents
9. incident_events
10. system_logs
```

Then add:

```text
11. evidence
12. anpr_results
13. rules
14. camera_health
15. system_metrics
16. nodes
17. audit_logs
```

I would actually make `nodes` part of the initial implementation if the backend is already running on both laptops.

---

# 43. Final Architecture

The resulting backend becomes:

```text
                    ┌───────────────┐
                    │    cameras    │
                    └───────┬───────┘
                            │
              ┌─────────────┴──────────────┐
              ▼                            ▼
      camera_streams                    zones
                                           │
                                           ▼
                                      zone_points


AI PIPELINE
     │
     ▼
detection_tracks
     │
     ▼
observations
     │
     ▼
events
     │
     ▼
incident_events
     │
     ▼
incidents
     │
     ├──────────────► evidence
     │
     └──────────────► anpr_results


SYSTEM
   │
   ├── nodes
   ├── camera_health
   ├── system_metrics
   ├── system_logs
   └── audit_logs


                         DATABASE
                            │
                            ▼
                         FastAPI
                     ┌──────┴──────┐
                     ▼             ▼
                 REST API       WebSocket
                     │             │
                     ▼             ▼
                Dashboard      Live Alerts
                     │
                     ▼
               Mobile Browser
```

This fits the existing IBVAP architecture particularly well because the backend is already intended to persist **incidents, observations, timeline data and camera metadata**, then expose REST APIs and WebSockets to the command-center dashboard. 

## The key architectural rule

**The database should record the story of what the surveillance system knows, not become the surveillance system itself.**

```text
Camera
  ↓
Observation
  ↓
Event
  ↓
Incident
  ↓
Evidence
  ↓
Operator Response

```
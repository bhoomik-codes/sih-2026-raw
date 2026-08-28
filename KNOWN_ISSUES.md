# KNOWN_ISSUES.md
# IBVAP — Known Issues Tracker

> Maintain this file throughout the project. Log every significant bug or unexpected behaviour.
> A well-maintained known-issues file demonstrates engineering maturity to SIH judges.

---

## Format

```
### ISSUE-XXX: Short title
- **Phase discovered:** Phase N
- **Severity:** Critical / High / Medium / Low
- **Status:** Open / Investigating / Fixed / Won't fix / Deferred
- **Description:** What happens
- **Root cause:** If known
- **Workaround:** If available
- **Fix:** Commit or PR if resolved
```

---

## Video Issues

### ISSUE-001: OpenCV `cap.read()` blocking indefinitely on RTSP network drop
- **Phase discovered:** Phase 1
- **Severity:** High
- **Status:** Fixed
- **Description:** In `apps/edge/video_source.py`, the reader thread uses `cap.read()` which is blocking. If the RTSP stream drops silently (network failure without TCP FIN), `cap.read()` can hang forever rather than returning `False`. This causes the internal RTSP Watchdog to never trigger a reconnect, freezing the camera permanently.
- **Root cause:** OpenCV backend lacks a built-in strict timeout for `read()`.
- **Workaround:** Restart the application if a camera goes offline and doesn't recover.
- **Fix:** Added active watchdog heartbeat monitor in `apps/edge/video_source.py` that releases capture on read timeout, set OpenCV buffer/timeout properties, and made `read()` default to non-blocking `get_nowait()`.

---

## GPU Issues

_No GPU issues logged yet._

---

## Tracking Issues

### ISSUE-002: Unbounded memory leak in ByteTracker trajectories
- **Phase discovered:** Phase 2
- **Severity:** High
- **Status:** Fixed
- **Description:** In `cv/tracking/byte_tracker.py`, the tracker maintains a history of positions in `self._trajectories`. When a track becomes stale (the vehicle leaves the frame), the code explicitly skips deletion (`pass`) to handle temporary occlusions. However, it never cleans up completely lost tracks. Over hours of continuous operation, this dictionary will grow unboundedly, leading to a memory leak and eventually `OOM`.
- **Root cause:** Missing garbage collection for track IDs that haven't been seen for a long time (e.g., > 100 frames).
- **Workaround:** None currently.
- **Fix:** Implemented TTL frame-tracking (`_track_last_seen`) with automatic garbage collection of `self._trajectories` when tracks remain lost beyond `max(60, track_buffer * 2)` frames.

---

## ANPR Issues

### ISSUE-003: ANPR defaults to Mock Mode silently
- **Phase discovered:** Phase 5
- **Severity:** Medium
- **Status:** Fixed
- **Description:** `intelligence/anpr/engine.py` wraps `easyocr` in a `try/except ImportError` block. If the package isn't installed, it falls back to returning `MOCK-<tid>`. In a production deployment without `easyocr`, it will generate fake plate alerts without throwing an obvious system error.
- **Root cause:** Graceful degradation logic masks missing dependencies.
- **Workaround:** Ensure `easyocr` is manually installed on Edge nodes.
- **Fix:** Created `cv/anpr/plate_pipeline.py` with `PlateOCR` and `PlatePreprocessor` (CLAHE, bilateral filtering, deskewing), integrated with `intelligence/anpr/engine.py`, and added explicit `is_mock` logging and status attributes.

---

## Event Engine Issues

_No event engine issues logged yet._

---

## Incident & Threat Intelligence Issues

### ISSUE-005: Stale track garbage collection mismatch in IncidentGenerator
- **Phase discovered:** Phase 4 / Phase 10
- **Severity:** Medium
- **Status:** Fixed
- **Description:** `IncidentGenerator.cleanup_stale_tracks()` used a fixed 10-second grace period with `time.time()` checks, causing memory to retain stale tracks when `cleanup_stale_tracks(active_track_ids)` was called on disappearing objects.
- **Root cause:** Inconsistent method contract compared to virtual fence, line crossing, and loitering engines.
- **Workaround:** None needed.
- **Fix:** Refactored `cleanup_stale_tracks()` in `intelligence/incidents/generator.py` to immediately purge unreferenced track IDs from `_event_buffer`, `_last_score`, `_last_incident_time`, and `_last_seen`.

---

## Video Streaming & Edge Processor Issues

### ISSUE-006: Frame stream bypass when local OpenCV display is active
- **Phase discovered:** Phase 9 / Phase 10
- **Severity:** High
- **Status:** Fixed
- **Description:** In `apps/edge/processor.py`, `_streamer.update_frame()` was nested in an `elif self._streamer:` branch under `if self._display:`. When local display was enabled, the MJPEG HTTP server received no updated frames, causing blank streams in the Command Center UI.
- **Root cause:** Exclusive `if/elif` branching between display and streaming outputs.
- **Workaround:** Pass `--no-display` when running edge nodes.
- **Fix:** Separated `self._streamer` frame encoding from `self._display` in `apps/edge/processor.py`, ensuring both local window and HTTP web streams receive annotated frames simultaneously.

---

## Backend Issues

### ISSUE-004: Sequential Timeout accumulation in MultiCameraManager
- **Phase discovered:** Phase 8
- **Severity:** Medium
- **Status:** Fixed
- **Description:** In `apps/edge/multi_camera_manager.py`, `get_latest_frames(timeout=0.05)` loops sequentially through all cameras and blocks up to `0.05s` on *each* empty queue. For 4 cameras, if queues are empty, it stalls the main inference loop for `0.2s` (a 5 FPS throttle).
- **Root cause:** Sequential blocking `queue.get()` calls instead of parallel polling.
- **Workaround:** Reduce the timeout to `0.0` or `0.01` to mitigate the delay.
- **Fix:** Updated `get_latest_frames()` and `read()` in `apps/edge/multi_camera_manager.py` to default to non-blocking (`timeout=0.0`) with global deadline distribution when a positive timeout is specified.

### ISSUE-007: Camera auto-registration and stream proxy route missing for external edge nodes
- **Phase discovered:** Phase 9 / Phase 10
- **Severity:** High
- **Status:** Fixed
- **Description:** When the Edge node connected to the backend via WebSocket from an independent terminal, the in-memory camera registry did not register the node, causing `GET /api/cameras` to return an empty array and the dashboard to show `NO_CAMERA_SELECTED`.
- **Root cause:** Backend only added cameras if manually created via REST API.
- **Workaround:** Add camera manually in dashboard UI.
- **Fix:** Added automatic camera registration upon receiving `edge_heartbeat` or `edge_event` packets in `apps/backend/main.py`, added stream redirection proxy `/api/streams/{camera_id}`, and mounted `/api/videos` for local video file serving.

---

## Deployment Issues

_No deployment issues logged yet._

---

## Expected / Pre-logged Risk Areas

The following are anticipated based on the project context document (§22).
They are not yet confirmed bugs but should be watched for:

| Area | Risk | Watch From |
|------|------|-----------|
| Video | RTSP timeout, frozen frames, FPS collapse | Phase 1 |
| GPU | CUDA OOM, TensorRT build failures, version mismatch | Phase 1+ |
| Tracking | ID switches, ghost tracks, duplicate tracks | Phase 2 |
| ANPR | OCR errors, incorrect plate crop, night failures | Phase 5 |
| Event Engine | Duplicate alerts, alert spam, false intrusions | Phase 3 |
| Backend | WebSocket disconnect, duplicate events | Phase 9 |
| Deployment | Missing CUDA libs, Docker GPU passthrough | Phase 9+ |

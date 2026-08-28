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
- **Status:** Open
- **Description:** In `apps/edge/video_source.py`, the reader thread uses `cap.read()` which is blocking. If the RTSP stream drops silently (network failure without TCP FIN), `cap.read()` can hang forever rather than returning `False`. This causes the internal RTSP Watchdog to never trigger a reconnect, freezing the camera permanently.
- **Root cause:** OpenCV backend lacks a built-in strict timeout for `read()`.
- **Workaround:** Restart the application if a camera goes offline and doesn't recover.
- **Fix:** Needs migration to GStreamer or an external threaded subprocess watchdog that hard-kills the thread if `last_frame_ts` gets too old.

---

## GPU Issues

_No GPU issues logged yet._

---

## Tracking Issues

### ISSUE-002: Unbounded memory leak in ByteTracker trajectories
- **Phase discovered:** Phase 2
- **Severity:** High
- **Status:** Open
- **Description:** In `cv/tracking/byte_tracker.py`, the tracker maintains a history of positions in `self._trajectories`. When a track becomes stale (the vehicle leaves the frame), the code explicitly skips deletion (`pass`) to handle temporary occlusions. However, it never cleans up completely lost tracks. Over hours of continuous operation, this dictionary will grow unboundedly, leading to a memory leak and eventually `OOM`.
- **Root cause:** Missing garbage collection for track IDs that haven't been seen for a long time (e.g., > 100 frames).
- **Workaround:** None currently.
- **Fix:** Implement a TTL (Time-To-Live) cache or explicitly `del self._trajectories[tid]` when `tid` is confirmed lost by ByteTrack.

---

## ANPR Issues

### ISSUE-003: ANPR defaults to Mock Mode silently
- **Phase discovered:** Phase 5
- **Severity:** Medium
- **Status:** Open
- **Description:** `intelligence/anpr/engine.py` wraps `easyocr` in a `try/except ImportError` block. If the package isn't installed, it falls back to returning `MOCK-<tid>`. In a production deployment without `easyocr`, it will generate fake plate alerts without throwing an obvious system error.
- **Root cause:** Graceful degradation logic masks missing dependencies.
- **Workaround:** Ensure `easyocr` is manually installed on Edge nodes.
- **Fix:** Add a strict startup check or warning banner in `apps/edge/main.py` if ANPR is enabled but the OCR engine is missing.

---

## Event Engine Issues

_No event engine issues logged yet._

---

## Backend Issues

### ISSUE-004: Sequential Timeout accumulation in MultiCameraManager
- **Phase discovered:** Phase 8
- **Severity:** Medium
- **Status:** Open
- **Description:** In `apps/edge/multi_camera_manager.py`, `get_latest_frames(timeout=0.05)` loops sequentially through all cameras and blocks up to `0.05s` on *each* empty queue. For 4 cameras, if queues are empty, it stalls the main inference loop for `0.2s` (a 5 FPS throttle).
- **Root cause:** Sequential blocking `queue.get()` calls instead of parallel polling.
- **Workaround:** Reduce the timeout to `0.0` or `0.01` to mitigate the delay.
- **Fix:** Poll all queues with `get_nowait()` in a non-blocking way, or use a unified multiplexed event queue.

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

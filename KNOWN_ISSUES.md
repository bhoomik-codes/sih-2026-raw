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

<!-- ISSUE-001 template -->
<!--
### ISSUE-001: RTSP timeout on reconnect
- **Phase discovered:** Phase 1
- **Severity:** High
- **Status:** Open
- **Description:** ...
-->

_No video issues logged yet._

---

## GPU Issues

_No GPU issues logged yet._

---

## Tracking Issues

_No tracking issues logged yet._

---

## ANPR Issues

_No ANPR issues logged yet._

---

## Event Engine Issues

_No event engine issues logged yet._

---

## Backend Issues

_No backend issues logged yet._

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

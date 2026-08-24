# apps/backend — API & Event Router (Laptop 1 or Laptop 2)

> **Phase:** 9 — not yet implemented  
> **Hardware target:** Can run on Laptop 1 alongside the edge node, or on Laptop 2

This is the central broker between the AI edge node and the dashboard.

## Planned Responsibilities

```
apps/edge (AI Node)
       ↓  WebSocket / internal events
   Event Receiver
   - Receives structured events from edge node
   - Validates and deduplicates events
         ↓
   Event Storage (PostgreSQL / SQLite)
   - Persists incidents, observations, and timeline
   - Stores metadata (camera_id, timestamp, risk_score, etc.)
         ↓
   REST API (FastAPI)
   - GET /incidents          — paginated incident history
   - GET /cameras            — camera status
   - GET /health             — system health
   - POST /cameras/{id}/fence — define virtual fence polygons
         ↓
   WebSocket Server
   - Pushes live events to the dashboard (apps/dashboard/)
   - Real-time alerts broadcast
```

## Planned Technology

```
FastAPI + Uvicorn
WebSockets (starlette)
SQLAlchemy + SQLite (dev) → PostgreSQL (production)
Pydantic models for event validation
```

## Event Schema (Draft)

```json
{
  "event_id": "INC-000142",
  "camera_id": "BOP-CAM-01",
  "event_type": "border_intrusion",
  "track_id": 23,
  "risk_score": 87,
  "severity": "HIGH",
  "contributing_events": [
    "restricted_zone_entry",
    "virtual_fence_crossing",
    "loitering",
    "night_time_activity"
  ],
  "capture_ts": "2026-08-24T21:46:00Z",
  "ingest_ts": "2026-08-24T21:46:00.412Z",
  "bbox": [120, 80, 280, 420]
}
```

## Timestamp Design (Three Clocks)

Each event stores three timestamps (see context §23):
- `capture_ts` — when the camera frame was captured
- `ingest_ts` — when the edge node processed the event  
- `display_ts` — when the dashboard received the WebSocket push

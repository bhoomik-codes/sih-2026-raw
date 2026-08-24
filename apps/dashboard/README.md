# apps/dashboard — Command & Control Center (Laptop 2)

> **Phase:** 9 — not yet implemented  
> **Hardware target:** Laptop 2 — Intel i5-1334U · Intel Iris Xe (no CUDA required)

The dashboard is the operator-facing interface. It runs in a browser on Laptop 2 and
connects to the backend WebSocket for live event streaming.

## Planned Responsibilities

```
apps/backend (WebSocket)
       ↓
   Live Camera Feeds
   - MJPEG streams from edge node
   - Annotated overlays (bounding boxes, track IDs)
         ↓
   Active Incidents Panel
   - Real-time alert cards
   - Risk score + contributing events
   - "Why did this alert fire?" explainability breakdown
         ↓
   Map View (Leaflet.js)
   - Camera locations on a map
   - Zone/fence overlays
   - Incident pins with severity colour
         ↓
   Incident Timeline
   - Chronological event log
   - Filterable by camera, severity, type
         ↓
   System Health Monitor
   - GPU utilization, VRAM, temperature
   - Per-camera FPS and status
   - Dropped frame rate
   - Edge node connection status
         ↓
   Admin Controls
   - Define/edit virtual fence polygons per camera
   - Configure alert thresholds
   - Camera on/off
```

## Planned Technology

```
React (Vite)
Leaflet.js — interactive map
WebSocket client (native browser API)
Recharts or Chart.js — metric graphs
Tailwind CSS or custom CSS
```

## Mock Data Mode

During early development (before backend is ready), the dashboard should have
a **mock mode** that replays pre-recorded event JSON fixtures so UI can be
built and iterated independently of the AI pipeline.

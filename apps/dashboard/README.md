# apps/dashboard — Tactical Command Center UI (Laptop 2)

> **Status:** Production Ready (Phase 9 & 10 Complete)  
> **Hardware target:** Laptop 2 — Intel i5-1334U · Intel Iris Xe (runs in browser, no GPU required)

The Command Center is an operator-facing, tactical web dashboard built with React 18, TypeScript, TailwindCSS, and Vite. It connects to the FastAPI backend over WebSockets and REST for live surveillance, real-time alert notifications, explainability insights, and camera administration.

---

## 🌟 Key Features

* **Multi-Camera Matrix:** Live MJPEG video stream grid with tactical HUD overlays, FPS counters, and AI bounding boxes.
* **Instant Incident Toasts:** Non-blocking audiovisual toast notifications for high-priority security breaches.
* **Incident Center & Explainability Modal:**
  * Animated SVG **Risk Score Gauge** (0–100).
  * Contributing events breakdown with weight scores (Zone Entry, Perimeter Crossing, Loitering, ANPR Watchlist).
  * One-click **Acknowledge Incident** workflow.
* **Camera Management:** Wizard to add, configure, start, and stop RTSP streams, local MP4 files, USB webcams, and mobile video feeds.
* **System Health:** Live CPU, memory, edge node connectivity, and database telemetry.

---

## ⚡ Running the Dashboard

```bash
cd apps/dashboard

# Install Node.js dependencies
npm install

# Start local development server (port 5173)
npm run dev

# Build production bundle
npm run build
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🛠️ Architecture & Modules

```
src/
├── api/                  # Axios/fetch REST clients for backend endpoints
│   ├── cameras.ts        # GET/POST /api/cameras, start/stop streams
│   ├── events.ts         # GET /api/events
│   ├── incidents.ts      # GET /api/incidents, acknowledge
│   └── metrics.ts        # GET /api/metrics & /api/health
│
├── components/
│   ├── cameras/          # LiveStream HUD, CameraGrid, CameraConnectionWizard
│   ├── incidents/        # ActiveIncidentsList, IncidentCard, IncidentDetailModal
│   ├── events/           # EventTimeline, EventFilterDrawer
│   ├── common/           # AlertToast, SeverityBadge, LoadingState, EmptyState
│   └── layout/           # Header, NavigationTabs, MobileAwarenessView
│
├── hooks/                # Custom React hooks (useCameras, useIncidents, useHealth, etc.)
├── pages/                # CommandCenterPage, CameraManagementPage, IncidentCenterPage, etc.
└── websocket/            # Resilient auto-reconnecting WebSocket client (useWebSocket)
```

---

## 🔄 Proxy & Environment Configuration

Vite proxies `/api` and `/ws` requests to `http://localhost:8000` automatically:
* Check [vite.config.ts](file:///Users/apple/sih-2026-raw/apps/dashboard/vite.config.ts) for proxy rules.
* Check [.env](file:///Users/apple/sih-2026-raw/apps/dashboard/.env) for local environment overrides.

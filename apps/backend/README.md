# apps/backend — Command Center Backend & Event Router

> **Status:** Production Ready (Phase 9 & 10 Complete)  
> **Hardware target:** Laptop 1 (runs alongside Edge Node on port 8000) or Central Server

The FastAPI backend serves as the real-time event broker, persistence engine, camera proxy, and REST API server connecting Edge AI processing nodes with the Command Center Dashboard.

---

## 🏗️ Architecture & Responsibilities

```
  Edge AI Processing Node(s)
          │
          │ WebSocket (`/ws` telemetry)
          ▼
┌─────────────────────────────────────────────────────────────┐
│                 FASTAPI BACKEND (`apps/backend/main.py`)    │
│                                                             │
│  ├── WebSocket Multiplexer (`/ws`)                          │
│  │   - Ingests `edge_heartbeat`, `edge_event`, `edge_metrics`│
│  │   - Real-time broadcast to connected Dashboard clients   │
│  │   - Auto-registers active camera nodes                   │
│  │                                                          │
│  ├── Database Persistence Layer (`apps/backend/db.py`)      │
│  │   - Supabase & PostgreSQL relational persistence         │
│  │   - Stores cameras, events, incidents, audit logs        │
│  │                                                          │
│  ├── Video & Stream Routing                                 │
│  │   - Camera stream redirect proxy (`/api/streams/{id}`)   │
│  │   - Static surveillance video file server (`/api/videos`) │
│  │                                                          │
│  └── RESTful Management APIs                                │
│      - `/api/cameras`     — List & manage camera sources    │
│      - `/api/events`      — Query latest detection events   │
│      - `/api/incidents`   — Query correlated security alerts│
│      - `/api/metrics`     — System & inference metrics      │
│      - `/api/health`      — Healthcheck & DB status         │
└─────────────────────────────────────────────────────────────┘
          │
          │ REST API & WebSocket Push
          ▼
  React Command Center Dashboard (`apps/dashboard/`)
```

---

## ⚡ Running the Backend

```bash
# Activate virtual environment
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate

# Start backend on 0.0.0.0:8000
uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
* Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
* Redoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📡 Key Endpoints

### 1. WebSockets
* `ws://localhost:8000/ws` — Bi-directional multiplexed channel. Edge nodes push heartbeats/events; Dashboards receive instant incident broadcasts.

### 2. Cameras
* `GET /api/cameras` — List all registered camera nodes and their stream URLs.
* `POST /api/cameras` — Register a new camera node.
* `POST /api/cameras/{id}/start` — Start edge inference process for camera.
* `POST /api/cameras/{id}/stop` — Terminate running camera process.
* `GET /api/streams/{id}` — Stream reverse proxy/redirect to the active MJPEG server.

### 3. Incidents & Events
* `GET /api/incidents` — Query active and historical security incidents (with joined contributing events).
* `GET /api/events` — Query raw chronological surveillance events.
* `GET /api/videos` — List local `.mp4` video files in `data/videos`.

### 4. Health & Telemetry
* `GET /api/health` — Returns node status, Supabase connection status, and resource usage.
* `GET /api/metrics` — Returns system performance metrics.

---

## 🗄️ Database Integration

The backend connects to **Supabase PostgreSQL** using Alembic migrations in `alembic/versions/`. Configure `.env`:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOi...
DATABASE_URL=postgresql+pg8000://postgres.xxx:password@aws-0-xx.pooler.supabase.com:6543/postgres
```

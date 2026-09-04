import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from apps.backend import db
except ImportError:
    import db

try:
    from apps.backend import face_utils
except ImportError:
    import face_utils

try:
    from apps.backend import blockchain
except ImportError:
    import blockchain


# Load Config
CONFIG_PATH = Path("configs/backend_default.yaml")
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
else:
    config = {
        "database": {"enabled": False},
        "mock": {"mock_camera_state": False, "mock_charts": False, "mock_alerts": False},
    }

app = FastAPI(title="IBVAP Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CameraLocation(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None


class Zone(BaseModel):
    name: str
    polygon: List[List[float]]
    classes: Optional[List[str]] = None
    severity: Optional[str] = None
    type: Optional[str] = None
    threshold_s: Optional[float] = None


class FenceLine(BaseModel):
    name: str
    start: List[float]
    end: List[float]
    direction: Optional[str] = "any"
    classes: Optional[List[str]] = None
    severity: Optional[str] = None


class ZonesPayload(BaseModel):
    zones: List[Zone]


class FencePayload(BaseModel):
    lines: List[FenceLine]


class CameraCreatePayload(BaseModel):
    camera_id: str
    name: str
    source_url: str
    source_type: str
    location: Optional[CameraLocation] = None
    inference_enabled: bool = True


class Camera(CameraCreatePayload):
    status: str = "OFFLINE"
    stream_url: Optional[str] = None
    zones: Optional[List[Zone]] = None
    lines: Optional[List[FenceLine]] = None


# ─── Face Registry Models ─────────────────────────────────────────────────────

class FaceRecord(BaseModel):
    id: str
    name: str
    role: str  # 'SOLDIER' | 'INTRUDER'
    notes: Optional[str] = None
    image_b64: Optional[str] = None      # Thumbnail (small jpeg b64)
    embedding_b64: Optional[str] = None  # LBPH histogram pickle b64 (edge only)
    created_at: str
    updated_at: Optional[str] = None


class CreateFacePayload(BaseModel):
    name: str
    role: str  # 'SOLDIER' | 'INTRUDER'
    notes: Optional[str] = None
    image_b64: str  # Full resolution image for embedding computation


class UpdateFacePayload(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    notes: Optional[str] = None


# ─── In-memory runtime state ──────────────────────────────────────────────────

# In-memory runtime state (must exist before any request handler runs)
cameras: Dict[str, Camera] = {}
processes: Dict[str, subprocess.Popen] = {}
active_connections: List[WebSocket] = []
next_stream_port = int(os.getenv("EDGE_STREAM_PORT_START", "8081"))
_START_TIME = time.time()
_latest_metrics: Dict[str, Any] = {}
_in_memory_events: List[Dict[str, Any]] = []
_in_memory_incidents: List[Dict[str, Any]] = []
_MEMORY_CAP = 200

# Face registry: {face_id -> FaceRecord}
_face_registry: Dict[str, FaceRecord] = {}


# Mount static video directory if exists
VIDEOS_DIR = Path("data/videos")
if VIDEOS_DIR.exists():
    app.mount("/api/videos/files", StaticFiles(directory=str(VIDEOS_DIR)), name="videos")


def _remember(store: List[Dict[str, Any]], item: Dict[str, Any]) -> None:
    store.insert(0, item)
    del store[_MEMORY_CAP:]


def _normalize_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
    """Map edge telemetry field names to the dashboard SystemMetrics shape."""
    fps = data.get("inference_fps") or data.get("fps") or 0.0
    return {
        "fps": fps,
        "inference_fps": fps,
        "inference_latency_ms": data.get("inference_latency_ms"),
        "preprocess_latency_ms": data.get("preprocess_latency_ms"),
        "total_latency_ms": data.get("end_to_end_latency_ms") or data.get("total_latency_ms"),
        "queue_depth": data.get("queue_depth"),
        "dropped_frames": data.get("dropped_frames"),
        "dropped_ratio": data.get("dropped_ratio"),
        "processed_frames": data.get("processed_frames") or data.get("num_detections"),
        "gpu_utilization_pct": data.get("gpu_utilization") or data.get("gpu_utilization_pct") or 0.0,
        "vram_used_mb": data.get("gpu_memory_used_mb") or data.get("vram_used_mb"),
        "vram_total_mb": data.get("vram_total_mb"),
        "gpu_temp_c": data.get("gpu_temperature_c") or data.get("gpu_temp_c"),
        "cpu_utilization_pct": data.get("cpu_percent") or data.get("cpu_utilization_pct") or 0.0,
        "ram_used_mb": data.get("ram_used_mb"),
        "ram_total_mb": data.get("ram_total_mb"),
        "ram_percent": data.get("ram_percent"),
        "detector_status": data.get("detector_status", "Active"),
        "tracker_status": data.get("tracker_status", "Active (ByteTrack)"),
        "timestamp": data.get("timestamp", time.time()),
        "camera_name": data.get("camera_name"),
        "active_cameras": data.get("active_cameras", 0),
    }


def _incident_key(inc: Dict[str, Any]) -> str:
    return str(inc.get("incident_id") or inc.get("id") or inc.get("incident_code") or "")


def _ensure_default_camera():
    """Ensure at least default camera is registered if store is empty."""
    pass


@app.get("/api/cameras", response_model=List[Camera])
async def get_cameras():
    return list(cameras.values())


@app.get("/api/cameras/{camera_id}", response_model=Camera)
async def get_camera(camera_id: str):
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cameras[camera_id]


@app.get("/api/streams/{camera_id}")
async def get_camera_stream(camera_id: str, request: Request):
    """Proxy or redirect stream endpoint for the given camera."""
    cam = cameras.get(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    stream_url = cam.stream_url or "http://127.0.0.1:8081/stream"
    host = request.headers.get("host", "127.0.0.1:8000").split(":")[0]
    stream_url = stream_url.replace("127.0.0.1", host).replace("localhost", host)
    
    return RedirectResponse(url=stream_url)


@app.get("/api/videos")
async def list_videos():
    """List available local surveillance video files."""
    if not VIDEOS_DIR.exists():
        return []
    video_files = []
    for f in VIDEOS_DIR.glob("*.mp4"):
        video_files.append({
            "filename": f.name,
            "path": str(f),
            "size_bytes": f.stat().st_size,
            "url": f"/api/videos/files/{f.name}"
        })
    return video_files


@app.get("/api/utils/select-file")
async def select_local_file():
    """Open a native OS file dialog to select a video file and return its absolute path."""
    import tkinter as tk
    from tkinter import filedialog
    import threading

    result = {"path": None}

    def open_dialog():
        root = tk.Tk()
        root.attributes("-topmost", True)
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Select Video File for Edge AI",
            filetypes=(
                ("Video files", "*.mp4 *.avi *.mkv *.mov *.webm"),
                ("All files", "*.*")
            )
        )
        result["path"] = file_path
        root.destroy()

    t = threading.Thread(target=open_dialog)
    t.start()
    t.join()

    if not result["path"]:
        raise HTTPException(status_code=400, detail="No file selected")
    
    return {"path": result["path"]}


@app.post("/api/cameras", response_model=Camera)
async def create_camera(payload: CameraCreatePayload):
    if payload.camera_id in cameras:
        raise HTTPException(status_code=400, detail="Camera already exists")
    cam = Camera(**payload.model_dump())
    cameras[payload.camera_id] = cam
    return cam


@app.delete("/api/cameras/{camera_id}")
async def delete_camera(camera_id: str):
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    if camera_id in processes:
        processes[camera_id].terminate()
        del processes[camera_id]
    del cameras[camera_id]
    return {"success": True}


@app.post("/api/cameras/{camera_id}/zones")
async def update_camera_zones(camera_id: str, payload: ZonesPayload):
    """Save polygon zones for a camera (in-memory)."""
    _ensure_default_camera()
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    cameras[camera_id].zones = payload.zones
    return cameras[camera_id]


@app.post("/api/cameras/{camera_id}/fence")
async def update_camera_fence(camera_id: str, payload: FencePayload):
    """Save virtual fence/tripwire lines for a camera (in-memory)."""
    _ensure_default_camera()
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    cameras[camera_id].lines = payload.lines
    return cameras[camera_id]


# ─── Face Registry Endpoints ──────────────────────────────────────────────────

@app.get("/api/faces", response_model=List[FaceRecord])
def list_faces():
    """Return all face records (thumbnails included, embeddings excluded for UI performance)."""
    results = []
    for rec in _face_registry.values():
        # Return a copy without the heavy embedding_b64 for UI listing
        results.append(
            FaceRecord(
                id=rec.id,
                name=rec.name,
                role=rec.role,
                notes=rec.notes,
                image_b64=rec.image_b64,
                embedding_b64=None,  # excluded from UI listing
                created_at=rec.created_at,
                updated_at=rec.updated_at,
            )
        )
    return results


@app.post("/api/faces", response_model=FaceRecord)
def create_face(payload: CreateFacePayload):
    """
    Enroll a new face in the registry.
    Accepts a base64-encoded image, computes an LBPH embedding, and stores
    a compressed thumbnail alongside the embedding for edge-engine matching.
    """
    if not payload.name or not payload.image_b64:
        raise HTTPException(status_code=400, detail="name and image_b64 are required")
    if payload.role not in ("SOLDIER", "INTRUDER"):
        raise HTTPException(status_code=400, detail="role must be SOLDIER or INTRUDER")

    # Compute embedding
    embedding_b64 = face_utils.compute_lbph_histogram(payload.image_b64)
    if embedding_b64 is None:
        raise HTTPException(status_code=422, detail="Failed to compute face embedding — check image quality")

    now = datetime.now(timezone.utc).isoformat()
    face_id = str(uuid.uuid4())

    # Keep thumbnail at original (let frontend resize as needed — avoid re-encoding here)
    record = FaceRecord(
        id=face_id,
        name=payload.name,
        role=payload.role,
        notes=payload.notes,
        image_b64=payload.image_b64,
        embedding_b64=embedding_b64,
        created_at=now,
        updated_at=now,
    )
    _face_registry[face_id] = record
    # Return without embedding for the API response
    return FaceRecord(
        id=record.id, name=record.name, role=record.role, notes=record.notes,
        image_b64=record.image_b64, created_at=record.created_at, updated_at=record.updated_at,
    )


@app.get("/api/faces/embeddings")
def get_face_embeddings():
    """
    Return all face records INCLUDING embeddings — used exclusively by the edge engine
    to sync its local recognition model. Not intended for the dashboard UI.
    """
    return [
        {
            "id": rec.id,
            "name": rec.name,
            "role": rec.role,
            "embedding_b64": rec.embedding_b64,
        }
        for rec in _face_registry.values()
        if rec.embedding_b64
    ]


@app.put("/api/faces/{face_id}", response_model=FaceRecord)
def update_face(face_id: str, payload: UpdateFacePayload):
    """Update name, role, or notes for an existing face record."""
    if face_id not in _face_registry:
        raise HTTPException(status_code=404, detail="Face record not found")
    rec = _face_registry[face_id]
    if payload.name is not None:
        rec.name = payload.name
    if payload.role is not None:
        if payload.role not in ("SOLDIER", "INTRUDER"):
            raise HTTPException(status_code=400, detail="role must be SOLDIER or INTRUDER")
        rec.role = payload.role
    if payload.notes is not None:
        rec.notes = payload.notes
    rec.updated_at = datetime.now(timezone.utc).isoformat()
    return FaceRecord(
        id=rec.id, name=rec.name, role=rec.role, notes=rec.notes,
        image_b64=rec.image_b64, created_at=rec.created_at, updated_at=rec.updated_at,
    )


@app.delete("/api/faces/{face_id}")
def delete_face(face_id: str):
    """Remove a face record from the registry."""
    if face_id not in _face_registry:
        raise HTTPException(status_code=404, detail="Face record not found")
    del _face_registry[face_id]
    return {"success": True}


@app.post("/api/cameras/{camera_id}/start")
async def start_camera(camera_id: str):
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")

    cam = cameras[camera_id]
    if camera_id in processes and processes[camera_id].poll() is None:
        raise HTTPException(status_code=400, detail="Camera already running")

    global next_stream_port
    assigned_port = next_stream_port
    next_stream_port += 1

    cmd = [
        sys.executable,
        "-m",
        "apps.edge.main",
        "--source",
        cam.source_url,
        "--camera-id",
        camera_id,
        "--stream-port",
        str(assigned_port),
    ]

    try:
        proc = subprocess.Popen(cmd)
        processes[camera_id] = proc
        cam.status = "ONLINE"
        cam.stream_url = f"http://127.0.0.1:{assigned_port}/stream"
    except Exception as e:
        cam.status = "ERROR"
        cam.stream_url = None
        raise HTTPException(status_code=500, detail=str(e))

    return {"success": True}


@app.post("/api/cameras/{camera_id}/stop")
async def stop_camera(camera_id: str):
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")

    cam = cameras[camera_id]
    if camera_id in processes:
        processes[camera_id].terminate()
        del processes[camera_id]

    cam.status = "OFFLINE"
    return {"success": True}


@app.get("/api/health")
async def get_health():
    db_status = "offline"
    if db.db_enabled():
        try:
            db.get_db().table("cameras").select("count", count="exact").limit(1).execute()
            db_status = "online"
        except Exception as e:
            db_status = f"error: {e}"

    cpu_usage = 0.0
    memory_usage = 0.0
    try:
        import psutil

        cpu_usage = float(psutil.cpu_percent(interval=None))
        memory_usage = float(psutil.virtual_memory().percent)
    except Exception:
        pass

    online_cameras = sum(1 for c in cameras.values() if str(c.status).upper() == "ONLINE")
    edge_connected = online_cameras > 0 or len(processes) > 0 or bool(_latest_metrics)
    gpu_usage = float(_latest_metrics.get("gpu_utilization_pct") or 0.0)

    return {
        "status": "healthy",
        "edge_node": "online" if edge_connected else "offline",
        "edge_node_connected": edge_connected,
        "active_cameras": online_cameras or len(cameras),
        "database": db_status,
        "database_provider": "supabase" if db.db_enabled() else "none",
        "cpu_usage": cpu_usage,
        "memory_usage": memory_usage,
        "gpu_usage": gpu_usage,
        "uptime_seconds": int(time.time() - _START_TIME),
    }


@app.get("/api/metrics")
async def get_metrics():
    if _latest_metrics:
        return _latest_metrics
    if config.get("mock", {}).get("mock_charts"):
        return {
            "fps": 0,
            "inference_fps": 0,
            "cpu_utilization_pct": 0,
            "gpu_utilization_pct": 0,
            "active_cameras": len(cameras),
        }
    return {}


@app.get("/api/incidents")
def get_incidents():
    if db.db_enabled():
        try:
            res = (
                db.get_db()
                .table("incidents")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            if res.data:
                return res.data
        except Exception as e:
            print(f"[Supabase DB] get_incidents error: {e}")
    return list(_in_memory_incidents)


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):
    for inc in _in_memory_incidents:
        if _incident_key(inc) == incident_id:
            return inc
    if db.db_enabled():
        try:
            res = (
                db.get_db()
                .table("incidents")
                .select("*")
                .eq("id", incident_id)
                .limit(1)
                .execute()
            )
            if res.data:
                return res.data[0]
        except Exception as e:
            print(f"[Supabase DB] get_incident error: {e}")
    raise HTTPException(status_code=404, detail="Incident not found")


@app.post("/api/incidents/{incident_id}/acknowledge")
def acknowledge_incident(incident_id: str):
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for inc in _in_memory_incidents:
        if _incident_key(inc) == incident_id:
            inc["status"] = "ACKNOWLEDGED"
            inc["acknowledged_at"] = now
            return inc
    if db.db_enabled():
        try:
            res = (
                db.get_db()
                .table("incidents")
                .select("*")
                .eq("id", incident_id)
                .limit(1)
                .execute()
            )
            if res.data:
                record = dict(res.data[0])
                record["status"] = "ACKNOWLEDGED"
                record["acknowledged_at"] = now
                db.get_db().table("incidents").upsert(record).execute()
                return record
        except Exception as e:
            print(f"[Supabase DB] acknowledge_incident error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=404, detail="Incident not found")


@app.get("/api/events")
def get_events():
    if db.db_enabled():
        try:
            res = (
                db.get_db()
                .table("events")
                .select("*")
                .order("event_ts", desc=True)
                .limit(50)
                .execute()
            )
            if res.data:
                return res.data
        except Exception as e:
            print(f"[Supabase DB] get_events error: {e}")
    return list(_in_memory_events[:50])


async def broadcast_ws_message(payload: dict, sender: Optional[WebSocket] = None):
    """Broadcast a JSON message to all connected dashboard and monitoring clients."""
    msg_str = json.dumps(payload)
    dead_connections = []
    for connection in active_connections:
        if connection != sender:
            try:
                await connection.send_text(msg_str)
            except Exception:
                dead_connections.append(connection)
    for dc in dead_connections:
        if dc in active_connections:
            active_connections.remove(dc)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)

    # Send handshake confirmation
    await websocket.send_text(
        json.dumps(
            {
                "type": "system",
                "message": "IBVAP Command Center WebSocket connected.",
                "timestamp": time.time(),
            }
        )
    )

    mock_alerts = config.get("mock", {}).get("mock_alerts", False)

    async def mock_generator():
        while True:
            await asyncio.sleep(3.0)
            if not mock_alerts or not active_connections:
                continue
            any_online = any(c.status == "ONLINE" for c in cameras.values()) or len(cameras) > 0
            if any_online:
                cam_id = list(cameras.keys())[0] if cameras else "CAM-01"
                evt_data = {
                    "event_id": f"EVT-{uuid.uuid4().hex[:6].upper()}",
                    "camera_id": cam_id,
                    "event_type": "virtual_fence_crossing",
                    "track_id": int(time.time() % 100),
                    "severity": "medium",
                    "rule_name": "zone:border_fence",
                    "timestamp": time.time(),
                }
                await broadcast_ws_message({"type": "event", "data": evt_data})

    mock_task = asyncio.create_task(mock_generator()) if mock_alerts else None

    try:
        while True:
            # Receive live telemetry or events from Edge nodes
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            node_id = msg.get("node_id", "UNKNOWN")
            data = msg.get("data", {})

            if msg_type == "edge_heartbeat":
                cam_id = data.get("camera_id", node_id)
                advertised_stream = data.get("stream_url")
                if cam_id not in cameras:
                    cameras[cam_id] = Camera(
                        camera_id=cam_id,
                        name=cam_id,
                        source_url=data.get("source_url", "data/videos/border_crossing_test.mp4"),
                        source_type=data.get("source_type", "file"),
                        status=data.get("status", "ONLINE"),
                        stream_url=advertised_stream or "http://127.0.0.1:8081/stream",
                        inference_enabled=True,
                    )
                else:
                    cameras[cam_id].status = data.get("status", "ONLINE")
                    if advertised_stream:
                        cameras[cam_id].stream_url = advertised_stream
                await broadcast_ws_message(
                    {
                        "type": "camera_status",
                        "camera_id": cam_id,
                        "status": data.get("status", "ONLINE"),
                        "fps": data.get("fps", 0.0),
                        "stream_url": cameras[cam_id].stream_url,
                        "timestamp": time.time(),
                    },
                    sender=websocket,
                )

            elif msg_type == "edge_event":
                _remember(_in_memory_events, dict(data))
                await broadcast_ws_message(
                    {
                        "type": "event",
                        "data": data,
                    },
                    sender=websocket,
                )

                # Persist to database if available
                if db.db_enabled():
                    try:
                        import datetime

                        cam_name = data.get("camera_name", node_id)
                        ts_val = data.get("timestamp", time.time())
                        iso_ts = datetime.datetime.fromtimestamp(
                            ts_val, tz=datetime.timezone.utc
                        ).isoformat()

                        # Ensure camera exists to satisfy foreign key constraints
                        try:
                            db.get_db().table("cameras").upsert(
                                {
                                    "id": cam_name,
                                    "camera_code": cam_name,
                                    "name": cam_name,
                                    "status": "ONLINE",
                                    "source_type": "file",
                                    "source_url": "data/videos/border_patrol.mp4",
                                }
                            ).execute()
                        except Exception:
                            pass

                        db.get_db().table("events").insert(
                            {
                                "id": f"evt_{uuid.uuid4().hex[:16]}",
                                "event_code": f"EVT-{uuid.uuid4().hex[:8].upper()}",
                                "event_type": data.get("event_type", "SURVEILLANCE_EVENT"),
                                "severity": data.get("severity", "LOW").upper(),
                                "track_id": str(data.get("track_id", 0)),
                                "camera_id": cam_name,
                                "capture_ts": iso_ts,
                                "event_ts": iso_ts,
                                "confidence": float(data.get("confidence", 1.0)),
                                "metadata": data.get("details", {}),
                            }
                        ).execute()
                    except Exception as db_err:
                        print(f"[Supabase DB] save_event error: {db_err}")

            elif msg_type == "edge_incident":
                incident_payload = dict(data)
                incident_payload.setdefault("status", "OPEN")
                incident_payload.setdefault(
                    "incident_id", incident_payload.get("id", f"INC-{uuid.uuid4().hex[:8].upper()}")
                )
                incident_payload.setdefault("camera_id", incident_payload.get("camera_name", node_id))
                
                # --- BLOCKCHAIN ANCHORING ---
                severity = str(incident_payload.get("severity", "LOW")).upper()
                if severity in ["HIGH", "CRITICAL"]:
                    try:
                        tx_hash, ev_hash = blockchain.anchor.anchor_evidence(incident_payload)
                        incident_payload["blockchain_tx_hash"] = tx_hash
                        incident_payload["evidence_hash"] = ev_hash
                    except Exception as e:
                        print(f"[Blockchain] Failed to anchor incident: {e}")
                
                _remember(_in_memory_incidents, incident_payload)
                await broadcast_ws_message(
                    {
                        "type": "incident",
                        "data": incident_payload,
                    },
                    sender=websocket,
                )

                if db.db_enabled():
                    try:
                        import datetime

                        cam_name = data.get("camera_name", node_id)
                        ts_val = data.get("timestamp", time.time())
                        iso_ts = datetime.datetime.fromtimestamp(
                            ts_val, tz=datetime.timezone.utc
                        ).isoformat()

                        # Ensure camera exists to satisfy foreign key constraints
                        try:
                            db.get_db().table("cameras").upsert(
                                {
                                    "id": cam_name,
                                    "camera_code": cam_name,
                                    "name": cam_name,
                                    "status": "ONLINE",
                                    "source_type": "file",
                                    "source_url": "data/videos/border_patrol.mp4",
                                }
                            ).execute()
                        except Exception:
                            pass

                        desc = data.get("summary", "")
                        if incident_payload.get("blockchain_tx_hash"):
                            desc += f"\n\n[Blockchain Anchor] Verified TxHash: {incident_payload['blockchain_tx_hash']}"

                        db.get_db().table("incidents").insert(
                            {
                                "id": f"inc_{uuid.uuid4().hex[:16]}",
                                "incident_code": data.get(
                                    "incident_id", f"INC-{uuid.uuid4().hex[:8].upper()}"
                                ),
                                "incident_type": data.get("incident_type", "BORDER_SECURITY_ALERT"),
                                "severity": data.get("severity", "MEDIUM").upper(),
                                "risk_score": float(data.get("risk_score", 0.0)),
                                "title": data.get("summary", "Border Security Alert"),
                                "description": desc,
                                "status": "OPEN",
                                "camera_id": cam_name,
                                "created_at": iso_ts,
                            }
                        ).execute()
                    except Exception as db_err:
                        print(f"[Supabase DB] save_incident error: {db_err}")

            elif msg_type == "edge_metrics":
                global _latest_metrics
                _latest_metrics = _normalize_metrics(data)
                await broadcast_ws_message(
                    {
                        "type": "metrics",
                        "data": _latest_metrics,
                    },
                    sender=websocket,
                )

                if db.db_enabled():
                    try:
                        import datetime
                        ts_val = data.get("timestamp", time.time())
                        iso_ts = datetime.datetime.fromtimestamp(
                            ts_val, tz=datetime.timezone.utc
                        ).isoformat()
                        
                        # Ensure node exists to satisfy foreign key constraints
                        try:
                            db.get_db().table("nodes").upsert(
                                {
                                    "id": node_id,
                                    "node_code": node_id,
                                    "name": f"Edge Node {node_id}",
                                    "node_type": "edge",
                                    "status": "ONLINE",
                                    "last_heartbeat_at": iso_ts
                                }
                            ).execute()
                        except Exception:
                            pass
                        
                        # Insert system_metrics
                        db.get_db().table("system_metrics").insert(
                            {
                                "id": f"met_{uuid.uuid4().hex[:16]}",
                                "node_id": node_id,
                                "timestamp": iso_ts,
                                "cpu_percent": float(data.get("cpu_percent", 0.0) or 0.0),
                                "ram_percent": float(data.get("ram_percent", 0.0) or 0.0),
                                "ram_used_mb": float(data.get("ram_used_mb", 0.0) or 0.0),
                                "gpu_utilization": float(data.get("gpu_utilization", 0.0) or 0.0),
                                "gpu_memory_used_mb": float(data.get("gpu_memory_used_mb", 0.0) or 0.0),
                                "gpu_temperature_c": float(data.get("gpu_temperature_c", 0.0) or 0.0),
                                "inference_fps": float(data.get("inference_fps", 0.0) or 0.0),
                                "active_cameras": int(data.get("active_cameras", 0) or 0),
                            }
                        ).execute()
                    except Exception as db_err:
                        print(f"[Supabase DB] save_metrics error: {db_err}")

    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
        if mock_task:
            mock_task.cancel()
    except Exception:
        if websocket in active_connections:
            active_connections.remove(websocket)
        if mock_task:
            mock_task.cancel()

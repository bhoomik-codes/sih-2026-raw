import asyncio
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from apps.backend import db
except ImportError:
    import db


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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CameraLocation(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None


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


from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Mount static video directory if exists
VIDEOS_DIR = Path("data/videos")
if VIDEOS_DIR.exists():
    app.mount("/api/videos/files", StaticFiles(directory=str(VIDEOS_DIR)), name="videos")


def _ensure_default_camera():
    """Ensure at least default camera is registered if store is empty."""
    if not cameras:
        if db.db_enabled():
            try:
                res = db.get_db().table("cameras").select("*").execute()
                for c in (res.data or []):
                    cid = c.get("id") or c.get("camera_code", "CAM-01")
                    cameras[cid] = Camera(
                        camera_id=cid,
                        name=c.get("name", cid),
                        source_url=c.get("source_url", "data/videos/border_crossing_test.mp4"),
                        source_type=c.get("source_type", "file"),
                        status=c.get("status", "ONLINE"),
                        stream_url=f"http://localhost:8081/stream",
                        inference_enabled=True,
                    )
            except Exception:
                pass
        if not cameras:
            cameras["BOP-CAM-01"] = Camera(
                camera_id="BOP-CAM-01",
                name="Border Outpost Cam 01",
                source_url="data/videos/border_crossing_test.mp4",
                source_type="file",
                status="ONLINE",
                stream_url="http://localhost:8081/stream",
                inference_enabled=True,
            )


@app.get("/api/cameras", response_model=List[Camera])
async def get_cameras():
    _ensure_default_camera()
    return list(cameras.values())


@app.get("/api/cameras/{camera_id}", response_model=Camera)
async def get_camera(camera_id: str):
    _ensure_default_camera()
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cameras[camera_id]


@app.get("/api/streams/{camera_id}")
async def get_camera_stream(camera_id: str):
    """Proxy or redirect stream endpoint for the given camera."""
    _ensure_default_camera()
    cam = cameras.get(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    stream_url = cam.stream_url or "http://localhost:8081/stream"
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
        "--stream-port",
        str(assigned_port),
    ]

    try:
        proc = subprocess.Popen(cmd)
        processes[camera_id] = proc
        cam.status = "ONLINE"
        cam.stream_url = f"http://localhost:{assigned_port}/stream"
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
    # Health endpoint can always work, returning real backend state
    db_status = "offline"
    if db.db_enabled():
        try:
            # Simple ping to Supabase
            db.get_db().table("cameras").select("count", count="exact").limit(1).execute()
            db_status = "online"
        except Exception as e:
            db_status = f"error: {e}"

    return {
        "status": "healthy",
        "edge_node": "online" if len(processes) > 0 else "offline",
        "database": db_status,
        "database_provider": "supabase" if db.db_enabled() else "none",
        "cpu_usage": 0,
        "memory_usage": 0,
        "gpu_usage": 0,
        "uptime_seconds": 0,
    }


@app.get("/api/metrics")
async def get_metrics():
    if config.get("mock", {}).get("mock_charts"):
        return {
            "active_cameras": len(cameras),
            "total_detections_today": 12450,
            "active_incidents": 2,
            "system_health": "Optimal",
        }

    if not config.get("database", {}).get("enabled"):
        raise HTTPException(
            status_code=501,
            detail="Metrics database not connected. Enable 'mock_charts' in config or implement DB integration.",
        )

    return {}


@app.get("/api/incidents")
async def get_incidents():
    if db.db_enabled():
        try:
            # Query the unified incidents table and join incident_events
            res = (
                db.get_db()
                .table("incidents")
                .select("*, incident_events(event_id, contribution_score, is_primary, events(*))")
                .order("created_at", desc=True)
                .execute()
            )
            return res.data
        except Exception as e:
            print(f"[Supabase DB] get_incidents error: {e}")

    if config.get("mock", {}).get("mock_alerts"):
        return []  # Return mock array if mock is enabled

    return []


@app.get("/api/events")
async def get_events():
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
            return res.data
        except Exception as e:
            print(f"[Supabase DB] get_events error: {e}")

    if config.get("mock", {}).get("mock_alerts"):
        return []  # Return mock array if mock is enabled

    return []


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
                if cam_id not in cameras:
                    cameras[cam_id] = Camera(
                        camera_id=cam_id,
                        name=cam_id,
                        source_url="data/videos/border_crossing_test.mp4",
                        source_type="file",
                        status=data.get("status", "ONLINE"),
                        stream_url=data.get("stream_url", "http://localhost:8081/stream"),
                        inference_enabled=True,
                    )
                else:
                    cameras[cam_id].status = data.get("status", "ONLINE")
                    if "stream_url" in data:
                        cameras[cam_id].stream_url = data["stream_url"]
                await broadcast_ws_message(
                    {
                        "type": "camera_status",
                        "camera_id": cam_id,
                        "status": data.get("status", "ONLINE"),
                        "fps": data.get("fps", 0.0),
                        "timestamp": time.time(),
                    },
                    sender=websocket,
                )

            elif msg_type == "edge_event":
                # Forward to dashboard
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
                await broadcast_ws_message(
                    {
                        "type": "incident",
                        "data": data,
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
                                "description": data.get("summary", ""),
                                "status": "OPEN",
                                "camera_id": cam_name,
                                "created_at": iso_ts,
                            }
                        ).execute()
                    except Exception as db_err:
                        print(f"[Supabase DB] save_incident error: {db_err}")

            elif msg_type == "edge_metrics":
                await broadcast_ws_message(
                    {
                        "type": "metrics",
                        "data": data,
                    },
                    sender=websocket,
                )

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

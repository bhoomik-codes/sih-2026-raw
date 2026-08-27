import asyncio
import subprocess
import time
import json
import uuid
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from apps.backend.db import db

# Load Config
CONFIG_PATH = Path("configs/backend_default.yaml")
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
else:
    config = {
        "database": {"enabled": True},
        "mock": {"mock_camera_state": False, "mock_charts": False, "mock_alerts": False}
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Supabase DB connection
    connected = await db.connect()
    if connected:
        # Preload cameras from DB into memory
        try:
            saved_cams = await db.get_cameras()
            for cam_dict in saved_cams:
                cam = Camera(**cam_dict)
                cam.status = "OFFLINE"
                cameras[cam.camera_id] = cam
        except Exception as e:
            print(f"[Supabase DB] Error loading existing cameras: {e}")
    yield
    # Shutdown
    await db.disconnect()
    for proc in processes.values():
        if proc.poll() is None:
            proc.terminate()


app = FastAPI(title="IBVAP Backend", lifespan=lifespan)

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


# In-memory store
cameras: Dict[str, Camera] = {}
processes: Dict[str, subprocess.Popen] = {}
active_connections: List[WebSocket] = []
next_stream_port = 8081


@app.get("/api/cameras", response_model=List[Camera])
async def get_cameras():
    if db.is_connected:
        try:
            db_cams = await db.get_cameras()
            if db_cams:
                # Merge runtime status with db data
                for c in db_cams:
                    cid = c["camera_id"]
                    if cid in cameras:
                        c["status"] = cameras[cid].status
                        c["stream_url"] = cameras[cid].stream_url
                return [Camera(**c) for c in db_cams]
        except Exception as e:
            print(f"[Supabase DB] get_cameras error: {e}")
    return list(cameras.values())


@app.get("/api/cameras/{camera_id}", response_model=Camera)
async def get_camera(camera_id: str):
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cameras[camera_id]


@app.post("/api/cameras", response_model=Camera)
async def create_camera(payload: CameraCreatePayload):
    if payload.camera_id in cameras:
        raise HTTPException(status_code=400, detail="Camera already exists")
    cam = Camera(**payload.model_dump())
    cameras[payload.camera_id] = cam
    if db.is_connected:
        try:
            await db.upsert_camera(cam.model_dump())
        except Exception as e:
            print(f"[Supabase DB] upsert_camera error: {e}")
    return cam


@app.delete("/api/cameras/{camera_id}")
async def delete_camera(camera_id: str):
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    if camera_id in processes:
        processes[camera_id].terminate()
        del processes[camera_id]
    del cameras[camera_id]
    if db.is_connected:
        try:
            await db.delete_camera(camera_id)
        except Exception as e:
            print(f"[Supabase DB] delete_camera error: {e}")
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
        "-m", "apps.edge.main",
        "--source", cam.source_url,
        "--stream-port", str(assigned_port)
    ]
    
    try:
        proc = subprocess.Popen(cmd)
        processes[camera_id] = proc
        cam.status = "ONLINE"
        cam.stream_url = f"http://localhost:{assigned_port}/stream"
        if db.is_connected:
            await db.upsert_camera(cam.model_dump())
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
    if db.is_connected:
        await db.upsert_camera(cam.model_dump())
    return {"success": True}


@app.get("/api/health")
async def get_health():
    db_health = await db.check_health()
    return {
        "status": "healthy",
        "edge_node": "online" if len(processes) > 0 else "offline",
        "database": db_health.get("status", "offline"),
        "database_provider": "supabase",
        "cpu_usage": 0,
        "memory_usage": 0,
        "gpu_usage": 0,
        "uptime_seconds": 0
    }


@app.get("/api/metrics")
async def get_metrics():
    if config.get("mock", {}).get("mock_charts"):
        return {
            "active_cameras": len(cameras),
            "total_detections_today": 12450,
            "active_incidents": 2,
            "system_health": "Optimal"
        }
    
    # Return metrics based on active state / database
    return {
        "active_cameras": sum(1 for c in cameras.values() if c.status == "ONLINE"),
        "total_detections_today": 0,
        "active_incidents": 0,
        "system_health": "Optimal" if db.is_connected else "Degraded"
    }


@app.get("/api/incidents")
async def get_incidents():
    if db.is_connected:
        try:
            return await db.get_incidents()
        except Exception as e:
            print(f"[Supabase DB] get_incidents error: {e}")
            
    if config.get("mock", {}).get("mock_alerts"):
        return []
    
    return []


@app.get("/api/events")
async def get_events():
    if db.is_connected:
        try:
            return await db.get_events()
        except Exception as e:
            print(f"[Supabase DB] get_events error: {e}")
            
    if config.get("mock", {}).get("mock_alerts"):
        return []
        
    return []


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    mock_alerts = config.get("mock", {}).get("mock_alerts")
    
    if not mock_alerts:
        await websocket.send_text(json.dumps({
            "type": "system",
            "message": "WebSocket connected to IBVAP Backend & Supabase."
        }))
        
    try:
        while True:
            await asyncio.sleep(2.0)
            
            if mock_alerts:
                any_online = any(c.status == "ONLINE" for c in cameras.values())
                if any_online:
                    event_data = {
                        "event_id": f"EVT-{uuid.uuid4().hex[:6]}",
                        "camera_id": list(cameras.keys())[0],
                        "event_type": "virtual_fence_crossing",
                        "track_id": int(time.time() % 100),
                        "severity": "medium",
                        "rule_name": "zone:border_fence",
                        "timestamp": time.time()
                    }
                    if db.is_connected:
                        await db.save_event(event_data)
                    event = {
                        "type": "event",
                        "data": event_data
                    }
                    for connection in active_connections:
                        await connection.send_text(json.dumps(event))
                        
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)

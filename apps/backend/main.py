import asyncio
import subprocess
import time
import json
import uuid
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load Config
CONFIG_PATH = Path("configs/backend_default.yaml")
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
else:
    config = {
        "database": {"enabled": False},
        "mock": {"mock_camera_state": False, "mock_charts": False, "mock_alerts": False}
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

# In-memory store
cameras: Dict[str, Camera] = {}
processes: Dict[str, subprocess.Popen] = {}
active_connections: List[WebSocket] = []
next_stream_port = 8081

@app.get("/api/cameras", response_model=List[Camera])
async def get_cameras():
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
        ".\\.venv\\Scripts\\python.exe",
        "-m", "apps.edge.main",
        "--source", cam.source_url,
        "--stream-port", str(assigned_port)
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
    return {
        "status": "healthy",
        "edge_node": "online" if len(processes) > 0 else "offline",
        "database": "online" if config.get("database", {}).get("enabled") else "offline",
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
    
    if not config.get("database", {}).get("enabled"):
        raise HTTPException(status_code=501, detail="Metrics database not connected. Enable 'mock_charts' in config or implement DB integration.")
    
    return {}

@app.get("/api/incidents")
async def get_incidents():
    if config.get("mock", {}).get("mock_alerts"):
        return [] # Return mock array if mock is enabled
    
    if not config.get("database", {}).get("enabled"):
        raise HTTPException(status_code=501, detail="Incident database not connected. Enable 'mock_alerts' in config or implement DB integration.")
    return []

@app.get("/api/events")
async def get_events():
    if config.get("mock", {}).get("mock_alerts"):
        return [] # Return mock array if mock is enabled
        
    if not config.get("database", {}).get("enabled"):
        raise HTTPException(status_code=501, detail="Event database not connected. Enable 'mock_alerts' in config or implement DB integration.")
    return []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    # Check if mock alerts are enabled
    mock_alerts = config.get("mock", {}).get("mock_alerts")
    
    if not mock_alerts:
        # If no mock data, just send a system message
        await websocket.send_text(json.dumps({
            "type": "system",
            "message": "WebSocket connected. Real-time edge node event integration is pending. Enable 'mock_alerts' in backend config for simulated data."
        }))
        
    try:
        while True:
            await asyncio.sleep(2.0)
            
            if mock_alerts:
                # Generate mock events if any camera is online
                any_online = any(c.status == "ONLINE" for c in cameras.values())
                if any_online:
                    event = {
                        "type": "event",
                        "data": {
                            "event_id": f"EVT-{uuid.uuid4().hex[:6]}",
                            "camera_id": list(cameras.keys())[0],
                            "event_type": "virtual_fence_crossing",
                            "track_id": int(time.time() % 100),
                            "severity": "medium",
                            "rule_name": "zone:border_fence",
                            "timestamp": time.time()
                        }
                    }
                    for connection in active_connections:
                        await connection.send_text(json.dumps(event))
                        
    except WebSocketDisconnect:
        active_connections.remove(websocket)

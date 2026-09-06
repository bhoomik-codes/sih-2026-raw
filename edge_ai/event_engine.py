import time
import cv2
import json
import logging
import threading
import queue
import requests
import uuid

logger = logging.getLogger("EdgeAI.EventEngine")

class EventEngine:
    def __init__(self, backend_url: str, cooldown_sec: float = 10.0, max_queue_size: int = 50):
        self.backend_url = backend_url
        self.cooldown_sec = cooldown_sec
        self.event_queue = queue.Queue(maxsize=max_queue_size)
        self.last_seen = {}  # {(camera_id, track_id, event_type): timestamp}
        self.last_face_seen = {} # {camera_id: timestamp}
        
        # Metrics
        self.events_generated = 0
        self.events_dropped = 0
        self.last_upload_latency_ms = 0.0
        
        self.session = requests.Session()
        self._login()
        
        self.worker_thread = threading.Thread(target=self._upload_worker, daemon=True)
        self.worker_thread.start()

    def _login(self):
        try:
            res = self.session.post(
                f"{self.backend_url}/auth/login",
                data={"username": "admin", "password": "admin123"},
                timeout=5.0
            )
            if res.status_code == 200:
                logger.info("EventEngine authenticated with backend.")
            else:
                logger.error(f"EventEngine auth failed: {res.status_code}")
        except Exception as e:
            logger.error(f"EventEngine auth exception: {e}")

    def process_detections(self, frame, tracked_objects, camera_id: int):
        now = time.time()
        for obj in tracked_objects:
            cls_name = obj.get('class_name', '')
            
            # Map classes to event types
            if cls_name == 'person':
                event_type = 'PERSON_DETECTED'
            elif cls_name in ['car', 'truck', 'bus', 'motorcycle', 'bicycle']:
                event_type = 'VEHICLE_DETECTED'
            elif cls_name == 'face':
                event_type = 'FACE_DETECTED'
            else:
                continue

            track_id = obj.get('track_id', -1)
            
            # Special throttle for faces per camera (since face tracking can be unstable)
            if event_type == 'FACE_DETECTED':
                last_cam_face_time = self.last_face_seen.get(camera_id, 0)
                if (now - last_cam_face_time) > 5.0: # 5 sec throttle
                    self.last_face_seen[camera_id] = now
                    self._generate_event(frame, obj, camera_id, event_type, extra=None)
                continue

            if track_id == -1:
                continue

            key = (camera_id, track_id, event_type)
            last_time = self.last_seen.get(key, 0)
            
            if (now - last_time) > self.cooldown_sec:
                self.last_seen[key] = now
                self._generate_event(frame, obj, camera_id, event_type, extra=None)
                
    def _generate_event(self, frame, obj, camera_id: int, event_type: str):
        self.events_generated += 1
        
        # Capture snapshot
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            logger.warning(f"Failed to encode snapshot for event {event_type} cam {camera_id}")
            return
            
        frame_bytes = buffer.tobytes()
        
        event_data = {
            "event_id": uuid.uuid4().hex,
            "camera_id": camera_id,
            "event_type": event_type,
            "bbox": json.dumps(obj.get('bbox', {})),
            "confidence": obj.get('confidence', 0.0),
            "track_id": obj.get('track_id', -1),
        }
        
        try:
            self.event_queue.put_nowait((event_data, frame_bytes))
            logger.info(f"Queued event: {event_type} for camera {camera_id} track #{obj.get('track_id')}")
        except queue.Full:
            self.events_dropped += 1
            logger.warning("Event queue full. Dropped low-priority duplicate event.")

    def _upload_worker(self):
        while True:
            try:
                event_data, frame_bytes = self.event_queue.get()
                
                t0 = time.perf_counter()
                
                files = {
                    'file': ('snapshot.jpg', frame_bytes, 'image/jpeg')
                }
                data = {
                    'event_data': json.dumps(event_data)
                }
                
                res = self.session.post(
                    f"{self.backend_url}/events/with_snapshot",
                    files=files,
                    data=data,
                    timeout=5.0
                )
                
                if res.status_code == 401:
                    # re-login and retry once
                    logger.warning("EventEngine auth expired. Re-authenticating...")
                    self._login()
                    res = self.session.post(
                        f"{self.backend_url}/events/with_snapshot",
                        files=files,
                        data=data,
                        timeout=5.0
                    )
                
                upload_time_ms = (time.perf_counter() - t0) * 1000.0
                self.last_upload_latency_ms = round(upload_time_ms, 2)
                
                if res.status_code == 201:
                    logger.info(f"Successfully uploaded event {event_data['event_id']} in {self.last_upload_latency_ms}ms")
                else:
                    logger.error(f"Failed to upload event {event_data['event_id']}: HTTP {res.status_code} {res.text}")
                    
                self.event_queue.task_done()
            except Exception as e:
                logger.error(f"Exception in event upload worker: {e}")
                time.sleep(1.0) # avoid tight loop on persistent failure

    def get_metrics(self) -> dict:
        return {
            "events_generated": self.events_generated,
            "events_dropped": self.events_dropped,
            "event_queue_size": self.event_queue.qsize(),
            "snapshot_upload_latency_ms": self.last_upload_latency_ms
        }

"""
intelligence.anpr.engine
------------------------
Automatic Number Plate Recognition (ANPR) Engine.

Optimizes GPU usage by NOT running OCR on every frame. Instead, it tracks vehicles
and buffers candidate crops. When the vehicle leaves the scene or has been tracked
for a sufficient number of frames, it selects the largest crop (closest to camera)
and runs OCR once.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
import numpy as np
import cv2

from cv.detection.base import Detection
from intelligence.events.base import EventSeverity, EventType, SurveillanceEvent

logger = logging.getLogger(__name__)

try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False
    logger.warning("easyocr not installed. ANPR will run in mock mode.")


class _VehicleTrackBuffer:
    def __init__(self, track_id: int):
        self.track_id = track_id
        # List of (area, crop_image, timestamp, bbox)
        self.crops: List[Tuple[float, np.ndarray, float, Tuple[float,float,float,float]]] = []
        self.last_seen = time.time()
        self.ocr_run = False
        
    def add_crop(self, frame: np.ndarray, det: Detection):
        x1, y1, x2, y2 = det.bbox.as_xyxy()
        h, w = frame.shape[:2]
        # Ensure within bounds
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(w, int(x2)), min(h, int(y2))
        
        if x2 > x1 and y2 > y1:
            crop = frame[y1:y2, x1:x2].copy()
            area = (x2 - x1) * (y2 - y1)
            self.crops.append((area, crop, det.timestamp, (x1,y1,x2,y2)))
            self.last_seen = det.timestamp


class ANPREngine:
    """
    Manages vehicle crop buffering and OCR execution.
    """
    def __init__(self, config: dict, camera_name: str):
        self._camera_name = camera_name
        
        anpr_cfg = config.get("anpr_engine", {})
        self._enabled = bool(anpr_cfg.get("enabled", True))
        self._min_area = int(anpr_cfg.get("min_crop_area", 4000))
        self._vehicle_classes = {"car", "truck", "bus", "motorcycle"}
        
        # Mock watchlist for testing Risk scoring
        self._watchlist = set(anpr_cfg.get("watchlist", []))
        
        self._buffers: Dict[int, _VehicleTrackBuffer] = {}
        
        if self._enabled and HAS_EASYOCR:
            logger.info("Initializing EasyOCR Reader...")
            self._reader = easyocr.Reader(['en'], gpu=True)
        else:
            self._reader = None

    def update(self, frame: np.ndarray, detections: List[Detection]) -> List[SurveillanceEvent]:
        if not self._enabled:
            return []

        events: List[SurveillanceEvent] = []
        now = time.time()
        active_tids = set()

        # Update buffers
        for det in detections:
            if det.track_id is None or det.class_name not in self._vehicle_classes:
                continue
            
            tid = det.track_id
            active_tids.add(tid)
            
            if tid not in self._buffers:
                self._buffers[tid] = _VehicleTrackBuffer(tid)
                
            self._buffers[tid].add_crop(frame, det)
            
            # If we've collected enough frames (e.g. 15), run OCR early to provide real-time feed
            if len(self._buffers[tid].crops) >= 15 and not self._buffers[tid].ocr_run:
                event = self._run_ocr_for_track(tid, det)
                if event:
                    events.append(event)
                self._buffers[tid].ocr_run = True

        # Process tracks that have left the scene (not seen for 2 seconds)
        stale_tids = [tid for tid, buf in self._buffers.items() if tid not in active_tids and (now - buf.last_seen) > 2.0]
        
        for tid in stale_tids:
            if not self._buffers[tid].ocr_run:
                # Need a dummy detection to base the event on
                if self._buffers[tid].crops:
                    last_crop_info = self._buffers[tid].crops[-1]
                    bbox = last_crop_info[3]
                    # We create a pseudo-detection for the event
                    from cv.detection.base import BBox
                    dummy_det = Detection(
                        bbox=BBox(x1=bbox[0], y1=bbox[1], x2=bbox[2], y2=bbox[3]),
                        class_id=2, class_name="vehicle", confidence=1.0, frame_id=0, timestamp=now, track_id=tid
                    )
                    event = self._run_ocr_for_track(tid, dummy_det)
                    if event:
                        events.append(event)
            # Cleanup
            del self._buffers[tid]

        return events

    def _run_ocr_for_track(self, tid: int, det: Detection) -> Optional[SurveillanceEvent]:
        buf = self._buffers[tid]
        
        # Filter crops by min_area
        valid_crops = [c for c in buf.crops if c[0] >= self._min_area]
        if not valid_crops:
            return None
            
        # Select crop with largest area (closest to camera)
        best_crop_info = max(valid_crops, key=lambda x: x[0])
        best_img = best_crop_info[1]
        
        plate_text = ""
        
        if self._reader:
            # Run EasyOCR
            results = self._reader.readtext(best_img)
            # Find the result with highest confidence or concatenate
            if results:
                # Sort by confidence
                best_result = max(results, key=lambda x: x[2])
                plate_text = best_result[1].upper().replace(" ", "")
        else:
            # Mock mode
            plate_text = f"MOCK-{tid}"

        if not plate_text:
            return None

        # Determine severity based on watchlist
        severity = EventSeverity.CRITICAL if plate_text in self._watchlist else EventSeverity.LOW

        logger.info("ANPR READ | Track #%d | Plate: %s", tid, plate_text)

        return SurveillanceEvent(
            event_type=EventType.VEHICLE_ANPR,
            severity=severity,
            track_id=tid,
            camera_name=self._camera_name,
            timestamp=det.timestamp,
            frame_id=det.frame_id,
            location=det.bbox.bottom_center,
            class_name=det.class_name,
            confidence=det.confidence,
            rule_name="anpr",
            details={"plate": plate_text, "matched_watchlist": plate_text in self._watchlist}
        )

"""
intelligence.events.face_detection
----------------------------------
Engine for emitting face detection events with appropriate debounce/cooldown.
"""

import time
import logging
from typing import List, Dict

from cv.detection.base import Detection
from intelligence.events.base import EventSeverity, EventType, SurveillanceEvent

logger = logging.getLogger(__name__)

class FaceDetectionEngine:
    """
    Monitors tracked face detections and generates debounced FACE_DETECTED events.
    
    Cooldown prevents spamming notifications for the same tracked person.
    """
    
    COOLDOWN_SECONDS = 15.0
    
    def __init__(self, camera_name: str) -> None:
        self.camera_name = camera_name
        # State: {track_id: timestamp_of_last_event}
        self.last_event_times: Dict[int, float] = {}

    def update(self, detections: List[Detection]) -> List[SurveillanceEvent]:
        events: List[SurveillanceEvent] = []
        now = time.time()
        
        for det in detections:
            if det.class_name != "face" or det.track_id is None:
                continue
                
            last_time = self.last_event_times.get(det.track_id, 0.0)
            if (now - last_time) >= self.COOLDOWN_SECONDS:
                self.last_event_times[det.track_id] = now
                
                # Emit event
                event = SurveillanceEvent(
                    event_type=EventType.FACE_DETECTED,
                    severity=EventSeverity.LOW,
                    track_id=det.track_id,
                    camera_name=self.camera_name,
                    timestamp=det.timestamp,
                    frame_id=det.frame_id,
                    location=det.bbox.center,
                    class_name="face",
                    confidence=det.confidence,
                    rule_name="face_detection:debounce",
                    details={"bbox": det.bbox.as_xywh()}
                )
                events.append(event)
                
        return events
        
    def cleanup_stale_tracks(self, active_track_ids: set) -> None:
        stale = [tid for tid in self.last_event_times if tid not in active_track_ids]
        for tid in stale:
            del self.last_event_times[tid]

"""
intelligence.events.loitering
------------------------------
Loitering detection: fires when a tracked object remains in a zone
beyond a configurable time threshold.

This is a time-based event, not a single-frame observation.
The clock starts when the object enters the zone and fires when it
exceeds the threshold.

Key design decisions:
  - Uses real-world time (Unix timestamp from Detection.timestamp), NOT frame count.
    This makes the threshold independent of FPS and frame-skip settings.
  - A separate loitering zone can be different from the virtual fence zone.
    (You might want a warning zone that's larger than the intrusion zone.)
  - Repeated events are suppressed per track: once LOITERING fires, it won't
    fire again for the same track until it leaves and re-enters the zone.

Config structure (from YAML):
    event_engine:
      loitering_zones:
        - name: "checkpoint_area"
          polygon: [[x1,y1],[x2,y2],[x3,y3],...]
          threshold_s: 10.0         # seconds before loitering fires
          classes: ["person"]
          severity: "medium"
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

import numpy as np

from cv.detection.base import Detection
from intelligence.events.base import EventSeverity, EventType, SurveillanceEvent
from intelligence.events.virtual_fence import _point_in_polygon


class _LoiteringZone:
    """Single loitering zone with per-track entry timestamps."""

    def __init__(
        self,
        name: str,
        polygon: np.ndarray,
        threshold_s: float,
        classes: Optional[Set[str]],
        severity: EventSeverity,
    ) -> None:
        self.name = name
        self.polygon = polygon
        self.threshold_s = threshold_s
        self.classes = classes
        self.severity = severity

        # track_id → entry timestamp (when they first entered the zone)
        self._entry_time: Dict[int, float] = {}
        # track_id → whether loitering has already fired for this visit
        self._alerted: Set[int] = set()

    def check(self, det: Detection, camera_name: str) -> Optional[SurveillanceEvent]:
        if det.track_id is None:
            return None
        if self.classes is not None and det.class_name not in self.classes:
            return None

        foot = (int(det.bbox.bottom_center[0]), int(det.bbox.bottom_center[1]))
        tid = det.track_id
        inside = _point_in_polygon(foot, self.polygon)

        if inside:
            if tid not in self._entry_time:
                self._entry_time[tid] = det.timestamp
                self._alerted.discard(tid)  # reset alert if re-entered

            # Check if threshold exceeded and not yet alerted
            dwell = det.timestamp - self._entry_time[tid]
            if dwell >= self.threshold_s and tid not in self._alerted:
                self._alerted.add(tid)
                return SurveillanceEvent(
                    event_type=EventType.LOITERING,
                    severity=self.severity,
                    track_id=tid,
                    camera_name=camera_name,
                    timestamp=det.timestamp,
                    frame_id=det.frame_id,
                    location=det.bbox.bottom_center,
                    class_name=det.class_name,
                    confidence=det.confidence,
                    rule_name=f"loitering:{self.name}",
                    details={
                        "zone": self.name,
                        "dwell_s": round(dwell, 1),
                        "threshold_s": self.threshold_s,
                    },
                )
        else:
            # Left the zone — clean up state
            self._entry_time.pop(tid, None)
            self._alerted.discard(tid)

        return None

    def cleanup_stale_tracks(self, active_track_ids: set) -> None:
        """Prune tracks that have left or become stale."""
        stale_tids = [tid for tid in list(self._entry_time.keys()) if tid not in active_track_ids]
        for tid in stale_tids:
            self._entry_time.pop(tid, None)
            self._alerted.discard(tid)


class LoiteringEngine:
    """
    Manages loitering detection zones.

    Args:
        zones_config: List of zone dicts from YAML.
        camera_name:  Camera identifier for event metadata.
    """

    def __init__(self, zones_config: List[dict], camera_name: str) -> None:
        self._camera_name = camera_name
        self._zones: List[_LoiteringZone] = []

        for z in zones_config:
            polygon = np.array(z["polygon"], dtype=np.int32)
            classes = set(z["classes"]) if z.get("classes") else None
            severity = EventSeverity[z.get("severity", "medium").upper()]
            threshold_s = float(z.get("threshold_s", 10.0))
            self._zones.append(_LoiteringZone(z["name"], polygon, threshold_s, classes, severity))

    def update(self, detections: List[Detection]) -> List[SurveillanceEvent]:
        """Check all detections against all loitering zones."""
        events: List[SurveillanceEvent] = []
        for det in detections:
            for zone in self._zones:
                event = zone.check(det, self._camera_name)
                if event:
                    events.append(event)
        return events

    def cleanup_stale_tracks(self, active_track_ids: set) -> None:
        """Prune stale tracks across all loitering zones."""
        for zone in self._zones:
            zone.cleanup_stale_tracks(active_track_ids)

    def draw(self, frame: "np.ndarray") -> None:
        """Draw loitering zones on the frame in-place."""
        import cv2

        for zone in self._zones:
            colour = (255, 165, 0)  # Orange
            cv2.polylines(frame, [zone.polygon.reshape(-1, 1, 2)], True, colour, 2)
            cx = int(zone.polygon[:, 0].mean())
            cy = int(zone.polygon[:, 1].mean())
            cv2.putText(
                frame,
                f"{zone.name} ({zone.threshold_s}s)",
                (cx - 30, cy),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                colour,
                1,
                cv2.LINE_AA,
            )

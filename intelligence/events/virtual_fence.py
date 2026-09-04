"""
intelligence.events.virtual_fence
-----------------------------------
Virtual fence (polygon zone) intrusion detection.

A VirtualFence is a user-defined polygon. When a tracked object's foot-point
(bottom-center of its bounding box) crosses into the polygon, a ZONE_ENTRY
event is raised. When it leaves, a ZONE_EXIT event is raised.

The fence operates on the bottom-center of the bounding box because that's the
most meaningful "ground contact" point for a person or vehicle.

Config structure (from YAML):
    event_engine:
      zones:
        - name: "restricted_zone_a"
          polygon: [[x1,y1],[x2,y2],[x3,y3],...]   # pixel coordinates
          classes: ["person"]                        # which classes trigger (null = all)
          severity: "high"
"""

from __future__ import annotations

from typing import List, Optional, Set, Tuple

import numpy as np

from cv.detection.base import Detection
from intelligence.events.base import EventSeverity, EventType, SurveillanceEvent


class _Zone:
    """Single polygon zone with state tracking per track_id."""

    def __init__(
        self,
        name: str,
        polygon: np.ndarray,
        classes: Optional[Set[str]],
        severity: EventSeverity,
    ) -> None:
        self.name = name
        self.polygon = polygon  # (N, 2) int32 pixel coords
        self.classes = classes  # None = all classes
        self.severity = severity
        # Tracks currently inside this zone
        self._inside: Set[int] = set()

    def check(self, det: Detection, camera_name: str, frame_wh: tuple[int, int]) -> Optional[SurveillanceEvent]:
        """
        Check if det's foot-point triggers an entry/exit event.

        Returns a SurveillanceEvent or None.
        """
        if det.track_id is None:
            return None

        # Class filter
        if self.classes is not None and det.class_name not in self.classes:
            return None

        # Scale detection coordinate from actual frame to the 1080p base coordinates of the polygon
        foot = det.bbox.bottom_center
        scale_x = 1920.0 / frame_wh[0] if frame_wh[0] > 0 else 1.0
        scale_y = 1080.0 / frame_wh[1] if frame_wh[1] > 0 else 1.0
        pt = (int(foot[0] * scale_x), int(foot[1] * scale_y))

        inside = _point_in_polygon(pt, self.polygon)
        was_inside = det.track_id in self._inside

        if inside and not was_inside:
            self._inside.add(det.track_id)
            return SurveillanceEvent(
                event_type=EventType.ZONE_ENTRY,
                severity=self.severity,
                track_id=det.track_id,
                camera_name=camera_name,
                timestamp=det.timestamp,
                frame_id=det.frame_id,
                location=foot,
                class_name=det.class_name,
                confidence=det.confidence,
                rule_name=f"zone:{self.name}",
                details={"zone": self.name},
            )
        elif not inside and was_inside:
            self._inside.discard(det.track_id)
            return SurveillanceEvent(
                event_type=EventType.ZONE_EXIT,
                severity=EventSeverity.LOW,
                track_id=det.track_id,
                camera_name=camera_name,
                timestamp=det.timestamp,
                frame_id=det.frame_id,
                location=foot,
                class_name=det.class_name,
                confidence=det.confidence,
                rule_name=f"zone:{self.name}",
                details={"zone": self.name},
            )
        return None

    def cleanup_stale_tracks(self, active_track_ids: set) -> None:
        """Discard inactive tracks from inside set."""
        self._inside = self._inside.intersection(active_track_ids)


class VirtualFenceEngine:
    """
    Manages one or more polygon zones and emits ZONE_ENTRY / ZONE_EXIT events.

    Args:
        zones_config: List of zone dicts from YAML (see module docstring).
        camera_name:  Camera identifier for event metadata.
    """

    def __init__(self, zones_config: List[dict], camera_name: str) -> None:
        self._camera_name = camera_name
        self._zones: List[_Zone] = []
        self.update_zones(zones_config)

    def update_zones(self, zones_config: List[dict]) -> None:
        new_zones = []
        for z in zones_config:
            polygon = np.array(z["polygon"], dtype=np.int32)
            classes = set(z["classes"]) if z.get("classes") else None
            severity_str = z.get("severity") or "high"
            severity = EventSeverity[severity_str.upper()]
            new_zones.append(_Zone(z["name"], polygon, classes, severity))
        self._zones = new_zones

    def update(self, detections: List[Detection], frame_wh: tuple[int, int] = (1920, 1080)) -> List[SurveillanceEvent]:
        """
        Check all detections against all zones.

        Returns:
            List of SurveillanceEvents fired this frame (may be empty).
        """
        events: List[SurveillanceEvent] = []
        for det in detections:
            for zone in self._zones:
                event = zone.check(det, self._camera_name, frame_wh)
                if event:
                    events.append(event)
        return events

    def cleanup_stale_tracks(self, active_track_ids: set) -> None:
        """Prune tracks no longer active from zone entry memory."""
        for zone in self._zones:
            zone.cleanup_stale_tracks(active_track_ids)

    def draw(self, frame: "np.ndarray", frame_wh: tuple[int, int] = (1920, 1080)) -> None:
        """Draw zone polygons on the frame in-place (for visualization)."""
        import cv2

        for zone in self._zones:
            colour = (0, 0, 220)  # Red for restricted zones
            
            # Scale from 1080p base coordinates down to actual frame
            scale_x = frame_wh[0] / 1920.0
            scale_y = frame_wh[1] / 1080.0
            scaled_poly = (zone.polygon * np.array([scale_x, scale_y])).astype(np.int32)

            cv2.polylines(frame, [scaled_poly.reshape(-1, 1, 2)], True, colour, 2)
            # Label zone name at the centroid
            cx = int(zone.polygon[:, 0].mean())
            cy = int(zone.polygon[:, 1].mean())
            cv2.putText(
                frame,
                zone.name,
                (cx - 10, cy),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                colour,
                1,
                cv2.LINE_AA,
            )


def _point_in_polygon(point: Tuple[int, int], polygon: np.ndarray) -> bool:
    """
    Ray-casting algorithm for point-in-polygon test.

    Args:
        point:   (x, y) integer pixel coordinate.
        polygon: (N, 2) numpy array of polygon vertices.

    Returns:
        True if point is inside the polygon.
    """
    import cv2

    result = cv2.pointPolygonTest(
        polygon.reshape(-1, 1, 2), (float(point[0]), float(point[1])), False
    )
    return result >= 0

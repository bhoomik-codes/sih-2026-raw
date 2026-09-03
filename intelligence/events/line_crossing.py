"""
intelligence.events.line_crossing
------------------------------------
Virtual line crossing detection.

A LineCrossing rule monitors when a tracked object's foot-point crosses
a defined line segment. The direction of crossing is recorded (A→B or B→A).

Uses a signed cross-product test to determine which side of the line an object
is on. A crossing event fires when the side changes between frames.

Config structure (from YAML):
    event_engine:
      lines:
        - name: "border_line"
          start: [x1, y1]          # pixel coordinates
          end:   [x2, y2]
          classes: ["person"]       # null = all classes
          direction: "any"          # "any", "AB" (A→B only), "BA" (B→A only)
          severity: "critical"
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from cv.detection.base import Detection
from intelligence.events.base import EventSeverity, EventType, SurveillanceEvent


def _cross_sign(
    line_start: Tuple[float, float],
    line_end: Tuple[float, float],
    point: Tuple[float, float],
) -> float:
    """
    Signed cross product of (line_end - line_start) × (point - line_start).
    Positive = point is to the left (side A), negative = right (side B).
    """
    dx = line_end[0] - line_start[0]
    dy = line_end[1] - line_start[1]
    px = point[0] - line_start[0]
    py = point[1] - line_start[1]
    return dx * py - dy * px


class _CrossingLine:
    """Single line crossing rule with per-track state."""

    def __init__(
        self,
        name: str,
        start: Tuple[float, float],
        end: Tuple[float, float],
        classes: Optional[Set[str]],
        direction: str,
        severity: EventSeverity,
    ) -> None:
        self.name = name
        self.start = start
        self.end = end
        self.classes = classes  # None = all
        self.direction = direction  # "any", "AB", "BA"
        self.severity = severity
        # Last known side per track_id: +1 (left/A) or -1 (right/B)
        self._last_side: Dict[int, float] = {}

    def check(self, det: Detection, camera_name: str) -> Optional[SurveillanceEvent]:
        if det.track_id is None:
            return None
        if self.classes is not None and det.class_name not in self.classes:
            return None

        foot = det.bbox.bottom_center
        side = _cross_sign(self.start, self.end, foot)
        tid = det.track_id

        prev = self._last_side.get(tid)
        self._last_side[tid] = side

        if prev is None:
            return None  # First time we see this track

        # Crossing detected when sign changes
        crossed = (prev > 0 and side < 0) or (prev < 0 and side > 0)
        if not crossed:
            return None

        # Determine direction
        crossing_dir = "AB" if (prev > 0 and side < 0) else "BA"
        if self.direction != "any" and self.direction != crossing_dir:
            return None  # Filtered by direction requirement

        return SurveillanceEvent(
            event_type=EventType.LINE_CROSSING,
            severity=self.severity,
            track_id=tid,
            camera_name=camera_name,
            timestamp=det.timestamp,
            frame_id=det.frame_id,
            location=foot,
            class_name=det.class_name,
            confidence=det.confidence,
            rule_name=f"line:{self.name}",
            details={
                "line": self.name,
                "direction": crossing_dir,
                "from_side": "A" if prev > 0 else "B",
                "to_side": "B" if side < 0 else "A",
            },
        )

    def cleanup_stale_tracks(self, active_track_ids: set) -> None:
        """Prune tracks no longer active from side tracking memory."""
        stale_tids = [tid for tid in list(self._last_side.keys()) if tid not in active_track_ids]
        for tid in stale_tids:
            self._last_side.pop(tid, None)


class LineCrossingEngine:
    """
    Manages virtual line crossing rules.

    Args:
        lines_config: List of line dicts from YAML.
        camera_name:  Camera identifier for event metadata.
    """

    def __init__(self, lines_config: List[dict], camera_name: str) -> None:
        self._camera_name = camera_name
        self._lines: List[_CrossingLine] = []
        self.update_lines(lines_config)

    def update_lines(self, lines_config: List[dict]) -> None:
        new_lines = []
        for lc in lines_config:
            start = tuple(lc["start"])
            end = tuple(lc["end"])
            classes = set(lc["classes"]) if lc.get("classes") else None
            direction = lc.get("direction", "any")
            severity = EventSeverity[lc.get("severity", "critical").upper()]
            new_lines.append(_CrossingLine(lc["name"], start, end, classes, direction, severity))
        self._lines = new_lines

    def update(self, detections: List[Detection]) -> List[SurveillanceEvent]:
        """Check all detections against all lines. Returns any crossing events."""
        events: List[SurveillanceEvent] = []
        for det in detections:
            for line in self._lines:
                event = line.check(det, self._camera_name)
                if event:
                    events.append(event)
        return events

    def cleanup_stale_tracks(self, active_track_ids: set) -> None:
        """Prune stale tracks across all lines."""
        for line in self._lines:
            line.cleanup_stale_tracks(active_track_ids)

    def draw(self, frame: "np.ndarray") -> None:
        """Draw crossing lines on the frame in-place."""
        import cv2

        for line in self._lines:
            p1 = (int(line.start[0]), int(line.start[1]))
            p2 = (int(line.end[0]), int(line.end[1]))
            colour = (0, 255, 255)  # Yellow
            cv2.line(frame, p1, p2, colour, 3)
            # Arrow indicating direction A→B
            mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
            cv2.putText(
                frame,
                f"{line.name}",
                (mid[0] + 5, mid[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                colour,
                1,
                cv2.LINE_AA,
            )

"""
intelligence.events.night_activity
-------------------------------------
Night-time activity detection (Phase 6).

Detects when tracked objects are moving during the configured nighttime window
and emits NIGHT_MOVEMENT events. This adds risk weight to incidents that occur
at night — a major red flag for border intrusion scenarios.

Config structure (from YAML):
    event_engine:
      night_activity:
        enabled: true
        night_start_hour: 20        # 8 PM (24h format)
        night_end_hour: 6           # 6 AM
        classes: ["person"]         # which classes trigger (null = all)
        severity: "high"
        cooldown_s: 30.0            # per-track cooldown (default 30s)
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Set

from cv.detection.base import Detection
from intelligence.events.base import EventSeverity, EventType, SurveillanceEvent

logger = logging.getLogger(__name__)


class NightActivityEngine:
    """
    Detects movement during nighttime hours and emits NIGHT_MOVEMENT events.

    Args:
        config:      The ``event_engine.night_activity`` dict from YAML.
        camera_name: Camera identifier for event metadata.
    """

    def __init__(self, config: dict, camera_name: str) -> None:
        self._camera_name = camera_name
        self._enabled = bool(config.get("enabled", True))

        self._night_start: int = int(config.get("night_start_hour", 20))
        self._night_end: int = int(config.get("night_end_hour", 6))

        raw_classes = config.get("classes", None)
        self._classes: Optional[Set[str]] = set(raw_classes) if raw_classes else None

        sev_str = config.get("severity", "high").upper()
        self._severity: EventSeverity = EventSeverity[sev_str]

        self._cooldown_s: float = float(config.get("cooldown_s", 30.0))

        # Per-track last-event time to avoid spamming
        self._last_event_time: Dict[int, float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_night(self) -> bool:
        """Return True if the current local time is within the night window."""
        hour = time.localtime().tm_hour
        if self._night_start > self._night_end:
            # Crosses midnight: e.g. 20-6
            return hour >= self._night_start or hour < self._night_end
        else:
            # Same day: e.g. 0-6
            return self._night_start <= hour < self._night_end

    def update(self, detections: List[Detection]) -> List[SurveillanceEvent]:
        """
        Emit a NIGHT_MOVEMENT event for each tracked detection during nighttime.

        Args:
            detections: Tracked detections (track_id must be set).

        Returns:
            List of NIGHT_MOVEMENT SurveillanceEvents (may be empty).
        """
        if not self._enabled or not detections:
            return []

        if not self.is_night():
            return []

        events: List[SurveillanceEvent] = []
        now = time.time()

        for det in detections:
            if det.track_id is None:
                continue

            # Class filter
            if self._classes is not None and det.class_name not in self._classes:
                continue

            # Cooldown: don't repeat event for the same track too quickly
            last = self._last_event_time.get(det.track_id, 0.0)
            if (now - last) < self._cooldown_s:
                continue

            self._last_event_time[det.track_id] = now
            foot = det.bbox.bottom_center

            events.append(
                SurveillanceEvent(
                    event_type=EventType.NIGHT_MOVEMENT,
                    severity=self._severity,
                    track_id=det.track_id,
                    camera_name=self._camera_name,
                    timestamp=det.timestamp,
                    frame_id=det.frame_id,
                    location=foot,
                    class_name=det.class_name,
                    confidence=det.confidence,
                    rule_name="night_activity",
                    details={"hour": time.localtime().tm_hour},
                )
            )

        return events

    def cleanup_stale_tracks(self, active_track_ids: set) -> None:
        """Remove stale track cooldown entries."""
        stale = [tid for tid in self._last_event_time if tid not in active_track_ids]
        for tid in stale:
            del self._last_event_time[tid]

    def draw(self, frame: "np.ndarray") -> None:  # noqa: F821
        """
        Draw a night-mode indicator on the frame if currently nighttime.
        Does nothing during daytime.
        """
        if not self._enabled or not self.is_night():
            return
        import cv2
        import numpy as np  # noqa: F401 (used via frame.shape)
        h, w = frame.shape[:2]
        # Draw a subtle night indicator in the top-right corner
        label = "[ NIGHT MODE ]"
        (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        x = w - tw - 12
        y = 24
        cv2.rectangle(frame, (x - 4, y - th - bl - 4), (x + tw + 4, y + 4), (30, 0, 60), cv2.FILLED)
        cv2.putText(
            frame, label, (x, y - bl),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 150, 255), 1, cv2.LINE_AA
        )

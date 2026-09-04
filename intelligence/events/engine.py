"""
intelligence.events.engine
----------------------------
EventEngine — the main orchestrator for Phases 3–6.

Composes VirtualFenceEngine, LineCrossingEngine, LoiteringEngine, and
NightActivityEngine into a single interface that the EdgeProcessor calls
once per inference step.

Responsibilities:
    - Initialize all sub-engines from YAML config.
    - Call each sub-engine's update() with the current tracked detections.
    - Collect and return all events fired in the current frame.
    - Provide draw() to annotate all zones/lines on a video frame.
    - Log events using structured logging (not print statements).

Config structure (from YAML):
    event_engine:
      camera_name: "BOP-CAM-01"    # auto-inherited from camera.name
      zones: [...]                  # see virtual_fence.py
      lines: [...]                  # see line_crossing.py
      loitering_zones: [...]        # see loitering.py
      night_activity:               # see night_activity.py (Phase 6)
        enabled: true
        night_start_hour: 20
        night_end_hour: 6
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np

from cv.detection.base import Detection
from intelligence.events.base import SurveillanceEvent
from intelligence.events.line_crossing import LineCrossingEngine
from intelligence.events.loitering import LoiteringEngine
from intelligence.events.night_activity import NightActivityEngine
from intelligence.events.virtual_fence import VirtualFenceEngine

logger = logging.getLogger(__name__)


class EventEngine:
    """
    Orchestrates all event detection rules (Phases 3–6).

    Args:
        config:      Full YAML config dict. Reads from ``event_engine`` block.
        camera_name: Camera identifier (typically from config.camera.name).
    """

    def __init__(self, config: dict, camera_name: str) -> None:
        ee_cfg = config.get("event_engine", {})
        self._camera_name = camera_name
        self._enabled = bool(ee_cfg.get("enabled", True))

        zones_cfg = ee_cfg.get("zones", [])
        lines_cfg = ee_cfg.get("lines", [])
        loiter_cfg = ee_cfg.get("loitering_zones", [])
        night_cfg = ee_cfg.get("night_activity", {})

        self._fence: VirtualFenceEngine = VirtualFenceEngine(zones_cfg, camera_name)
        self._crossing: LineCrossingEngine = LineCrossingEngine(lines_cfg, camera_name)
        self._loitering: LoiteringEngine = LoiteringEngine(loiter_cfg, camera_name)
        self._night: NightActivityEngine = NightActivityEngine(night_cfg, camera_name)

        logger.info(
            "EventEngine initialised  camera=%s  zones=%d  lines=%d  loitering=%d  night=%s",
            camera_name,
            len(zones_cfg),
            len(lines_cfg),
            len(loiter_cfg),
            bool(night_cfg.get("enabled", True)),
        )

    def update(self, detections: List[Detection]) -> List[SurveillanceEvent]:
        """
        Evaluate all rules against the latest tracked detections.

        Args:
            detections: Tracked detections from ByteTracker (track_id must be set).
            frame_wh: Tuple of (width, height) for the current frame.

        Returns:
            All SurveillanceEvents fired this frame (may be empty).
        """
    def update(self, detections: List[Detection], frame_wh: tuple[int, int] = (1920, 1080)) -> List[SurveillanceEvent]:
        if not self._enabled or not detections:
            return []

        events: List[SurveillanceEvent] = []
        events.extend(self._fence.update(detections, frame_wh))
        events.extend(self._crossing.update(detections, frame_wh))
        events.extend(self._loitering.update(detections, frame_wh))
        events.extend(self._night.update(detections, frame_wh))

        for ev in events:
            logger.info("EVENT  %s", ev)

        return events

    def cleanup_stale_tracks(self, active_track_ids: set) -> None:
        """Propagate stale-track cleanup to all sub-engines that maintain per-track state."""
        self._fence.cleanup_stale_tracks(active_track_ids)
        self._crossing.cleanup_stale_tracks(active_track_ids)
        self._loitering.cleanup_stale_tracks(active_track_ids)
        self._night.cleanup_stale_tracks(active_track_ids)

    def update_zones(self, zones_config: List[dict]) -> None:
        """Dynamically update polygon zones at runtime."""
        self._fence.update_zones(zones_config)

    def update_lines(self, lines_config: List[dict]) -> None:
        """Dynamically update tripwires at runtime."""
        self._crossing.update_lines(lines_config)

    def draw(self, frame: np.ndarray, frame_wh: tuple[int, int] = (1920, 1080)) -> None:
        """
        Draw all zones, lines, and overlays on the frame in-place.

        Call this before displaying or saving the annotated frame.
        """
        if not self._enabled:
            return
        self._fence.draw(frame, frame_wh)
        self._crossing.draw(frame, frame_wh)
        self._loitering.draw(frame, frame_wh)
        self._night.draw(frame, frame_wh)

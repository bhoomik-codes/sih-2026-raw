"""
tests.test_event_engine
-----------------------
Unit tests for the Phase 3 Event Intelligence layer.

Tests all three rule types:
  - VirtualFenceEngine (zone entry/exit)
  - LineCrossingEngine (line crossing direction)
  - LoiteringEngine (time-based dwell)
  - EventEngine (integrated orchestrator)
"""

import time
import pytest

from cv.detection.base import BBox, Detection
from intelligence.events.base import EventSeverity, EventType, SurveillanceEvent
from intelligence.events.virtual_fence import VirtualFenceEngine
from intelligence.events.line_crossing import LineCrossingEngine
from intelligence.events.loitering import LoiteringEngine
from intelligence.events.engine import EventEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_det(
    x1: float, y1: float, x2: float, y2: float,
    track_id: int = 1,
    class_name: str = "person",
    confidence: float = 0.9,
    frame_id: int = 1,
    timestamp: float = None,
) -> Detection:
    return Detection(
        bbox=BBox(x1=x1, y1=y1, x2=x2, y2=y2),
        class_id=0,
        class_name=class_name,
        confidence=confidence,
        frame_id=frame_id,
        timestamp=timestamp if timestamp is not None else time.time(),
        track_id=track_id,
    )


# Square zone: (100,100) to (300,300)
ZONE_CFG = [{
    "name": "test_zone",
    "polygon": [[100, 100], [300, 100], [300, 300], [100, 300]],
    "classes": ["person"],
    "severity": "high",
}]

# Horizontal line at y=200, full width
LINE_CFG = [{
    "name": "test_line",
    "start": [0, 200],
    "end":   [500, 200],
    "classes": None,
    "direction": "any",
    "severity": "critical",
}]

# Loitering zone matching ZONE_CFG
LOITER_CFG = [{
    "name": "test_loiter",
    "polygon": [[100, 100], [300, 100], [300, 300], [100, 300]],
    "threshold_s": 3.0,
    "classes": ["person"],
    "severity": "medium",
}]


# ---------------------------------------------------------------------------
# VirtualFenceEngine tests
# ---------------------------------------------------------------------------

class TestVirtualFence:

    def test_zone_entry_fires(self):
        engine = VirtualFenceEngine(ZONE_CFG, "CAM-01")
        # Person starts outside
        det_out = make_det(0, 0, 20, 20, track_id=1)
        engine.update([det_out])
        # Person enters zone (foot-point bottom_center = (110, 220) → inside)
        det_in = make_det(100, 200, 120, 220, track_id=1)
        events = engine.update([det_in])
        assert len(events) == 1
        assert events[0].event_type == EventType.ZONE_ENTRY

    def test_zone_exit_fires_after_entry(self):
        engine = VirtualFenceEngine(ZONE_CFG, "CAM-01")
        det_in = make_det(100, 200, 120, 220, track_id=1)
        engine.update([det_in])  # entry
        engine.update([det_in])  # still inside — no new event
        det_out = make_det(0, 0, 20, 20, track_id=1)
        events = engine.update([det_out])
        assert len(events) == 1
        assert events[0].event_type == EventType.ZONE_EXIT

    def test_no_duplicate_entry_event(self):
        engine = VirtualFenceEngine(ZONE_CFG, "CAM-01")
        det_in = make_det(100, 200, 120, 220, track_id=1)
        ev1 = engine.update([det_in])
        ev2 = engine.update([det_in])   # Same position — still inside
        assert len(ev1) == 1
        assert len(ev2) == 0

    def test_class_filter_ignores_car(self):
        engine = VirtualFenceEngine(ZONE_CFG, "CAM-01")
        det = make_det(100, 200, 120, 220, track_id=1, class_name="car")
        events = engine.update([det])
        assert len(events) == 0


# ---------------------------------------------------------------------------
# LineCrossingEngine tests
# ---------------------------------------------------------------------------

class TestLineCrossing:

    def test_crossing_fires_when_crossing_line(self):
        engine = LineCrossingEngine(LINE_CFG, "CAM-01")
        # Above the line (y < 200) — foot_y bottom is y2=190
        det_above = make_det(100, 150, 120, 190, track_id=1)
        engine.update([det_above])
        # Below the line (y > 200) — foot_y bottom is y2=220
        det_below = make_det(100, 200, 120, 220, track_id=1)
        events = engine.update([det_below])
        assert len(events) == 1
        assert events[0].event_type == EventType.LINE_CROSSING

    def test_no_crossing_without_side_change(self):
        engine = LineCrossingEngine(LINE_CFG, "CAM-01")
        det_above1 = make_det(100, 100, 120, 180, track_id=1)
        engine.update([det_above1])
        det_above2 = make_det(110, 100, 130, 180, track_id=1)
        events = engine.update([det_above2])
        assert len(events) == 0

    def test_direction_filter_AB_only(self):
        cfg = [{**LINE_CFG[0], "direction": "AB"}]
        engine = LineCrossingEngine(cfg, "CAM-01")
        # Go above → below (AB direction in our coord system with start=[0,200] end=[500,200]):
        # top-to-bottom = side changes from positive cross to negative cross
        # cross = dx*(py) - dy*(px) with dx=500, dy=0 → cross = 500*py
        # Above line: py < 0 → cross < 0 (side B)
        # Below line: py > 0 → cross > 0 (side A)
        # So top→bottom is B→A, which means direction "BA"
        det_above = make_det(100, 100, 120, 150, track_id=1)
        engine.update([det_above])
        det_below = make_det(100, 220, 120, 260, track_id=1)
        events = engine.update([det_below])
        # With direction="AB", B→A crossing should be filtered
        assert len(events) == 0

    def test_first_frame_no_event(self):
        engine = LineCrossingEngine(LINE_CFG, "CAM-01")
        det = make_det(100, 100, 120, 180, track_id=1)
        events = engine.update([det])
        assert len(events) == 0  # No previous position to compare


# ---------------------------------------------------------------------------
# LoiteringEngine tests
# ---------------------------------------------------------------------------

class TestLoitering:

    def test_loitering_fires_after_threshold(self):
        engine = LoiteringEngine(LOITER_CFG, "CAM-01")
        now = time.time()
        # Enter zone
        det1 = make_det(100, 200, 120, 220, track_id=1, timestamp=now)
        engine.update([det1])
        # Still inside after 5 seconds — should fire (threshold=3.0s)
        det2 = make_det(110, 210, 130, 230, track_id=1, timestamp=now + 5.0)
        events = engine.update([det2])
        assert len(events) == 1
        assert events[0].event_type == EventType.LOITERING
        assert events[0].details["dwell_s"] >= 3.0

    def test_loitering_does_not_fire_before_threshold(self):
        engine = LoiteringEngine(LOITER_CFG, "CAM-01")
        now = time.time()
        det1 = make_det(100, 200, 120, 220, track_id=1, timestamp=now)
        engine.update([det1])
        det2 = make_det(110, 210, 130, 230, track_id=1, timestamp=now + 1.0)
        events = engine.update([det2])
        assert len(events) == 0

    def test_loitering_suppresses_repeated_alerts(self):
        engine = LoiteringEngine(LOITER_CFG, "CAM-01")
        now = time.time()
        det1 = make_det(100, 200, 120, 220, track_id=1, timestamp=now)
        engine.update([det1])
        det2 = make_det(110, 210, 130, 230, track_id=1, timestamp=now + 5.0)
        events_first = engine.update([det2])
        det3 = make_det(115, 215, 135, 235, track_id=1, timestamp=now + 10.0)
        events_second = engine.update([det3])
        assert len(events_first) == 1
        assert len(events_second) == 0  # Already alerted — no repeat

    def test_loitering_resets_after_exit(self):
        engine = LoiteringEngine(LOITER_CFG, "CAM-01")
        now = time.time()
        det_in = make_det(100, 200, 120, 220, track_id=1, timestamp=now)
        engine.update([det_in])
        det_fire = make_det(110, 210, 130, 230, track_id=1, timestamp=now + 5.0)
        engine.update([det_fire])  # First loitering alert
        # Exit zone
        det_out = make_det(0, 0, 10, 10, track_id=1, timestamp=now + 6.0)
        engine.update([det_out])
        # Re-enter zone after a while
        det_reenter = make_det(100, 200, 120, 220, track_id=1, timestamp=now + 7.0)
        engine.update([det_reenter])
        # Wait threshold again
        det_fire2 = make_det(110, 210, 130, 230, track_id=1, timestamp=now + 12.0)
        events = engine.update([det_fire2])
        assert len(events) == 1  # Should fire again after re-entry


# ---------------------------------------------------------------------------
# EventEngine integration test
# ---------------------------------------------------------------------------

class TestEventEngine:

    def _make_config(self, zones=None, lines=None, loitering=None):
        return {
            "camera": {"name": "TEST-CAM"},
            "event_engine": {
                "enabled": True,
                "zones": zones or [],
                "lines": lines or [],
                "loitering_zones": loitering or [],
            }
        }

    def test_event_engine_disabled(self):
        config = {"camera": {"name": "TEST-CAM"}, "event_engine": {"enabled": False, "zones": ZONE_CFG, "lines": [], "loitering_zones": []}}
        engine = EventEngine(config, "TEST-CAM")
        det = make_det(100, 200, 120, 220, track_id=1)
        events = engine.update([det])
        assert len(events) == 0

    def test_event_engine_no_rules_no_events(self):
        config = self._make_config()
        engine = EventEngine(config, "TEST-CAM")
        det = make_det(100, 200, 120, 220, track_id=1)
        events = engine.update([det])
        assert len(events) == 0

    def test_event_engine_returns_zone_event(self):
        config = self._make_config(zones=ZONE_CFG)
        engine = EventEngine(config, "TEST-CAM")
        det_out = make_det(0, 0, 10, 10, track_id=1)
        engine.update([det_out])
        det_in = make_det(100, 200, 120, 220, track_id=1)
        events = engine.update([det_in])
        assert any(e.event_type == EventType.ZONE_ENTRY for e in events)

    def test_event_engine_returns_crossing_event(self):
        config = self._make_config(lines=LINE_CFG)
        engine = EventEngine(config, "TEST-CAM")
        det_above = make_det(100, 150, 120, 190, track_id=1)
        engine.update([det_above])
        det_below = make_det(100, 200, 120, 220, track_id=1)
        events = engine.update([det_below])
        assert any(e.event_type == EventType.LINE_CROSSING for e in events)

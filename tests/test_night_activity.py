"""tests/test_night_activity.py — Unit tests for NightActivityEngine (Phase 6)."""

from __future__ import annotations

import time
from unittest.mock import patch

from cv.detection.base import BBox, Detection
from intelligence.events.base import EventType
from intelligence.events.night_activity import NightActivityEngine


def _make_det(track_id: int = 1, class_name: str = "person") -> Detection:
    """Helper: create a minimal Detection for testing."""
    d = Detection(
        bbox=BBox(x1=100, y1=100, x2=200, y2=300),
        class_id=0,
        class_name=class_name,
        confidence=0.85,
        frame_id=1,
        timestamp=time.time(),
    )
    d.track_id = track_id
    return d


# ── is_night() tests ──────────────────────────────────────────────────────────


class TestIsNight:
    def test_is_night_at_22h(self):
        """22:00 is within the default 20-06 night window."""
        engine = NightActivityEngine(
            {"enabled": True, "night_start_hour": 20, "night_end_hour": 6},
            "CAM-01",
        )
        with patch("intelligence.events.night_activity.time") as mock_time:
            mock_time.localtime.return_value = time.struct_time((2026, 8, 26, 22, 0, 0, 0, 0, 0))
            mock_time.time.return_value = time.time()
            assert engine.is_night() is True

    def test_is_not_night_at_noon(self):
        """12:00 is outside the default night window."""
        engine = NightActivityEngine(
            {"enabled": True, "night_start_hour": 20, "night_end_hour": 6},
            "CAM-01",
        )
        with patch("intelligence.events.night_activity.time") as mock_time:
            mock_time.localtime.return_value = time.struct_time((2026, 8, 26, 12, 0, 0, 0, 0, 0))
            mock_time.time.return_value = time.time()
            assert engine.is_night() is False

    def test_is_night_at_3am(self):
        """3:00 AM crosses midnight — should still be night."""
        engine = NightActivityEngine(
            {"enabled": True, "night_start_hour": 20, "night_end_hour": 6},
            "CAM-01",
        )
        with patch("intelligence.events.night_activity.time") as mock_time:
            mock_time.localtime.return_value = time.struct_time((2026, 8, 26, 3, 0, 0, 0, 0, 0))
            mock_time.time.return_value = time.time()
            assert engine.is_night() is True

    def test_not_night_at_boundary_end(self):
        """6:00 AM is the end of the night window (exclusive)."""
        engine = NightActivityEngine(
            {"enabled": True, "night_start_hour": 20, "night_end_hour": 6},
            "CAM-01",
        )
        with patch("intelligence.events.night_activity.time") as mock_time:
            mock_time.localtime.return_value = time.struct_time((2026, 8, 26, 6, 0, 0, 0, 0, 0))
            mock_time.time.return_value = time.time()
            assert engine.is_night() is False


# ── update() tests ────────────────────────────────────────────────────────────


class TestNightActivityUpdate:
    def _engine_at_hour(self, hour: int, config: dict | None = None) -> NightActivityEngine:
        """Create engine and patch time.localtime to return a fixed hour."""
        cfg = config or {"enabled": True, "night_start_hour": 20, "night_end_hour": 6}
        return NightActivityEngine(cfg, "CAM-01")

    def test_no_events_during_day(self):
        """No NIGHT_MOVEMENT events should fire during daytime."""
        engine = NightActivityEngine(
            {"enabled": True, "night_start_hour": 20, "night_end_hour": 6},
            "CAM-01",
        )
        with patch.object(engine, "is_night", return_value=False):
            events = engine.update([_make_det()])
        assert events == []

    def test_events_fired_during_night(self):
        """NIGHT_MOVEMENT events should fire for every track during nighttime."""
        engine = NightActivityEngine(
            {"enabled": True, "night_start_hour": 20, "night_end_hour": 6},
            "CAM-01",
        )
        with patch.object(engine, "is_night", return_value=True):
            events = engine.update([_make_det(1), _make_det(2)])
        assert len(events) == 2
        assert all(ev.event_type == EventType.NIGHT_MOVEMENT for ev in events)

    def test_class_filter_skips_vehicles(self):
        """When classes=['person'], car detections should NOT fire NIGHT_MOVEMENT."""
        engine = NightActivityEngine(
            {"enabled": True, "night_start_hour": 20, "night_end_hour": 6, "classes": ["person"]},
            "CAM-01",
        )
        with patch.object(engine, "is_night", return_value=True):
            events = engine.update([_make_det(1, "car"), _make_det(2, "truck")])
        assert events == []

    def test_class_filter_passes_person(self):
        """When classes=['person'], person detections SHOULD fire NIGHT_MOVEMENT."""
        engine = NightActivityEngine(
            {"enabled": True, "night_start_hour": 20, "night_end_hour": 6, "classes": ["person"]},
            "CAM-01",
        )
        with patch.object(engine, "is_night", return_value=True):
            events = engine.update([_make_det(1, "person")])
        assert len(events) == 1
        assert events[0].event_type == EventType.NIGHT_MOVEMENT

    def test_cooldown_prevents_repeat(self):
        """Same track should not fire NIGHT_MOVEMENT twice within the cooldown window."""
        engine = NightActivityEngine(
            {"enabled": True, "night_start_hour": 20, "night_end_hour": 6, "cooldown_s": 60.0},
            "CAM-01",
        )
        det = _make_det(1)
        with patch.object(engine, "is_night", return_value=True):
            first = engine.update([det])
            second = engine.update([det])  # within cooldown
        assert len(first) == 1
        assert len(second) == 0

    def test_no_event_when_disabled(self):
        """Engine should produce no events when disabled."""
        engine = NightActivityEngine({"enabled": False}, "CAM-01")
        with patch.object(engine, "is_night", return_value=True):
            events = engine.update([_make_det()])
        assert events == []

    def test_no_event_for_untracked_detection(self):
        """Detections without track_id should be silently ignored."""
        engine = NightActivityEngine(
            {"enabled": True, "night_start_hour": 20, "night_end_hour": 6},
            "CAM-01",
        )
        det = Detection(
            bbox=BBox(x1=0, y1=0, x2=10, y2=10),
            class_id=0,
            class_name="person",
            confidence=0.9,
            frame_id=1,
            timestamp=time.time(),
        )
        # track_id is None by default
        with patch.object(engine, "is_night", return_value=True):
            events = engine.update([det])
        assert events == []


# ── cleanup_stale_tracks() tests ─────────────────────────────────────────────


class TestCleanupStaleTracks:
    def test_cleanup_removes_stale_cooldown(self):
        """Stale track IDs should be removed from the cooldown dict."""
        engine = NightActivityEngine(
            {"enabled": True, "night_start_hour": 20, "night_end_hour": 6, "cooldown_s": 60.0},
            "CAM-01",
        )
        with patch.object(engine, "is_night", return_value=True):
            engine.update([_make_det(1), _make_det(2)])

        assert 1 in engine._last_event_time
        assert 2 in engine._last_event_time

        engine.cleanup_stale_tracks({2})  # track 1 is gone

        assert 1 not in engine._last_event_time
        assert 2 in engine._last_event_time

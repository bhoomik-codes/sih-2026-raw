"""tests/test_multi_camera_manager.py — Unit tests for MultiCameraManager (Phase 8)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from apps.edge.multi_camera_manager import (
    CameraHealthRecord,
    MultiCameraManager,
)
from apps.edge.video_source import Frame
from pipelines.base import PipelineStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_frame(frame_id: int = 1) -> Frame:
    import numpy as np

    return Frame(
        data=np.zeros((64, 64, 3), dtype="uint8"),
        frame_id=frame_id,
        timestamp=time.time(),
    )


def _mock_pipeline(frames=None):
    """Return a mock pipeline that yields the provided frames on read()."""
    frames = frames or []
    frame_iter = iter(frames)

    mock = MagicMock()
    mock.status = PipelineStatus.IDLE
    mock.frames_dropped = 0

    def read_side_effect(timeout=0.05):
        try:
            return next(frame_iter)
        except StopIteration:
            return None

    mock.read.side_effect = read_side_effect
    mock.start.side_effect = lambda: setattr(mock, "status", PipelineStatus.RUNNING)
    mock.stop.side_effect = lambda: setattr(mock, "status", PipelineStatus.STOPPED)
    return mock


def _cameras_config():
    return [
        {"id": "CAM-01", "source": "file1.mp4", "name": "Camera 1", "pipeline": "opencv"},
        {"id": "CAM-02", "source": "file2.mp4", "name": "Camera 2", "pipeline": "opencv"},
    ]


# ---------------------------------------------------------------------------
# CameraHealthRecord tests
# ---------------------------------------------------------------------------


class TestCameraHealthRecord:
    def test_initial_values(self):
        rec = CameraHealthRecord("CAM-01")
        assert rec.camera_id == "CAM-01"
        assert rec.frames_received == 0
        assert rec.frames_dropped == 0
        assert rec.status == PipelineStatus.IDLE

    def test_fps_estimate_zero_before_start(self):
        rec = CameraHealthRecord("CAM-01")
        assert rec.fps_estimate == pytest.approx(0.0)

    def test_fps_estimate_after_frames(self):
        rec = CameraHealthRecord("CAM-01")
        rec.started_at = time.time() - 5.0  # simulate 5 seconds elapsed
        rec.frames_received = 50
        assert rec.fps_estimate == pytest.approx(10.0, abs=1.0)

    def test_repr_contains_camera_id(self):
        rec = CameraHealthRecord("CAM-01")
        assert "CAM-01" in repr(rec)


# ---------------------------------------------------------------------------
# MultiCameraManager tests
# ---------------------------------------------------------------------------


class TestMultiCameraManager:
    def _manager_with_mocks(self):
        """Create a MultiCameraManager with mocked pipelines."""
        cfg = _cameras_config()
        manager = MultiCameraManager.__new__(MultiCameraManager)
        manager._pipelines = {}
        manager._health = {}
        import threading

        manager._lock = threading.Lock()

        for cam in cfg:
            cid = cam["id"]
            mock = _mock_pipeline()
            manager._pipelines[cid] = mock
            manager._health[cid] = CameraHealthRecord(cid)

        return manager

    def test_camera_ids(self):
        cfg = _cameras_config()
        with patch("apps.edge.multi_camera_manager._create_pipeline") as mock_create:
            mock_create.side_effect = lambda c, cid: _mock_pipeline()
            manager = MultiCameraManager(cfg)
        assert set(manager.camera_ids) == {"CAM-01", "CAM-02"}

    def test_num_cameras(self):
        cfg = _cameras_config()
        with patch("apps.edge.multi_camera_manager._create_pipeline") as mock_create:
            mock_create.side_effect = lambda c, cid: _mock_pipeline()
            manager = MultiCameraManager(cfg)
        assert manager.num_cameras == 2

    def test_start_all_calls_start_on_each_pipeline(self):
        manager = self._manager_with_mocks()
        manager.start_all()
        for p in manager._pipelines.values():
            p.start.assert_called_once()

    def test_stop_all_calls_stop_on_each_pipeline(self):
        manager = self._manager_with_mocks()
        manager.start_all()
        manager.stop_all()
        for p in manager._pipelines.values():
            p.stop.assert_called_once()

    def test_read_returns_frame_when_available(self):
        manager = self._manager_with_mocks()
        expected = _make_frame(42)
        manager._pipelines["CAM-01"].read.side_effect = None
        manager._pipelines["CAM-01"].read.return_value = expected

        result = manager.read("CAM-01")
        assert result is expected

    def test_read_returns_none_for_unknown_camera(self):
        manager = self._manager_with_mocks()
        result = manager.read("UNKNOWN-CAM")
        assert result is None

    def test_get_latest_frames_returns_all_cameras(self):
        manager = self._manager_with_mocks()
        frames = manager.get_latest_frames()
        assert set(frames.keys()) == {"CAM-01", "CAM-02"}

    def test_frames_received_incremented(self):
        manager = self._manager_with_mocks()
        frame = _make_frame()
        manager._pipelines["CAM-01"].read.return_value = frame
        manager._pipelines["CAM-01"].read.side_effect = None

        manager.read("CAM-01")
        assert manager._health["CAM-01"].frames_received == 1

    def test_start_specific_camera(self):
        manager = self._manager_with_mocks()
        manager.start("CAM-01")
        manager._pipelines["CAM-01"].start.assert_called_once()
        manager._pipelines["CAM-02"].start.assert_not_called()

    def test_stop_specific_camera(self):
        manager = self._manager_with_mocks()
        manager.stop("CAM-01")
        manager._pipelines["CAM-01"].stop.assert_called_once()
        manager._pipelines["CAM-02"].stop.assert_not_called()

    def test_start_unknown_camera_raises(self):
        manager = self._manager_with_mocks()
        with pytest.raises(KeyError):
            manager.start("DOES_NOT_EXIST")

    def test_get_health_returns_record(self):
        manager = self._manager_with_mocks()
        health = manager.get_health("CAM-01")
        assert isinstance(health, CameraHealthRecord)
        assert health.camera_id == "CAM-01"

    def test_get_health_returns_none_for_unknown(self):
        manager = self._manager_with_mocks()
        assert manager.get_health("UNKNOWN") is None

    def test_len(self):
        manager = self._manager_with_mocks()
        assert len(manager) == 2

    def test_repr_contains_camera_ids(self):
        manager = self._manager_with_mocks()
        r = repr(manager)
        assert "CAM-01" in r
        assert "CAM-02" in r

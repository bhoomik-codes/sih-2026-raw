"""tests/test_pipelines.py — Unit tests for OpenCVPipeline and GStreamerPipeline (Phase 8)."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from pipelines.base import PipelineStatus, VideoPipelineBase
from pipelines.gstreamer.pipeline import GStreamerPipeline, _is_gstreamer_available
from pipelines.opencv.pipeline import OpenCVPipeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cam_config(source: str = "data/videos/test_video.mp4") -> dict:
    return {
        "source": source,
        "name": "Test Camera",
        "max_queue_size": 2,
        "reconnect_delay_s": 0.1,
    }


# ---------------------------------------------------------------------------
# VideoPipelineBase abstract interface tests
# ---------------------------------------------------------------------------


class TestVideoPipelineBase:
    def test_cannot_instantiate_abstract(self):
        """Direct instantiation of the ABC should raise TypeError."""
        with pytest.raises(TypeError):
            VideoPipelineBase({}, "CAM-01")

    def test_concrete_must_implement_start(self):
        """Subclass without start() should not be instantiatable."""

        class Incomplete(VideoPipelineBase):
            def stop(self):
                pass

            def read(self, timeout=0.05):
                return None

        with pytest.raises(TypeError):
            Incomplete({}, "CAM-01")

    def test_concrete_must_implement_stop(self):
        class Incomplete(VideoPipelineBase):
            def start(self):
                pass

            def read(self, timeout=0.05):
                return None

        with pytest.raises(TypeError):
            Incomplete({}, "CAM-01")

    def test_concrete_must_implement_read(self):
        class Incomplete(VideoPipelineBase):
            def start(self):
                pass

            def stop(self):
                pass

        with pytest.raises(TypeError):
            Incomplete({}, "CAM-01")

    def test_minimal_concrete_works(self):
        class Minimal(VideoPipelineBase):
            def start(self):
                self._status = PipelineStatus.RUNNING

            def stop(self):
                self._status = PipelineStatus.STOPPED

            def read(self, timeout=0.05):
                return None

        p = Minimal({}, "CAM-01")
        assert p.camera_id == "CAM-01"
        assert p.status == PipelineStatus.IDLE
        p.start()
        assert p.status == PipelineStatus.RUNNING
        p.stop()
        assert p.status == PipelineStatus.STOPPED


# ---------------------------------------------------------------------------
# OpenCVPipeline tests
# ---------------------------------------------------------------------------


class TestOpenCVPipeline:
    def _pipeline(self, source: str = "data/videos/test_video.mp4") -> OpenCVPipeline:
        return OpenCVPipeline(_make_cam_config(source), "CAM-01")

    def test_initial_status_is_idle(self):
        p = self._pipeline()
        assert p.status == PipelineStatus.IDLE

    def test_camera_id_set(self):
        p = self._pipeline()
        assert p.camera_id == "CAM-01"

    def test_name_from_config(self):
        p = self._pipeline()
        assert p.name == "Test Camera"

    def test_start_changes_status_to_running(self):
        p = self._pipeline()
        with patch.object(p._video_source, "start"):
            p.start()
        assert p.status == PipelineStatus.RUNNING

    def test_stop_changes_status_to_stopped(self):
        p = self._pipeline()
        with patch.object(p._video_source, "start"):
            p.start()
        with patch.object(p._video_source, "stop"):
            p.stop()
        assert p.status == PipelineStatus.STOPPED

    def test_start_idempotent(self):
        """Calling start() twice should not raise."""
        p = self._pipeline()
        with patch.object(p._video_source, "start"):
            p.start()
            p.start()  # Second call should be ignored
        assert p.status == PipelineStatus.RUNNING

    def test_read_returns_none_when_no_frames(self):
        """read() should return None if the internal queue is empty."""
        p = self._pipeline()
        result = p.read(timeout=0.01)
        assert result is None

    def test_frames_dropped_initially_zero(self):
        p = self._pipeline()
        assert p.frames_dropped == 0

    def test_repr_contains_camera_id(self):
        p = self._pipeline()
        assert "CAM-01" in repr(p)


# ---------------------------------------------------------------------------
# GStreamerPipeline tests
# ---------------------------------------------------------------------------


class TestGStreamerPipeline:
    def _pipeline(self, source: str = "data/videos/test_video.mp4") -> GStreamerPipeline:
        return GStreamerPipeline(_make_cam_config(source), "CAM-GST-01")

    def test_initial_status_is_idle(self):
        p = self._pipeline()
        assert p.status == PipelineStatus.IDLE

    def test_camera_id_set(self):
        p = self._pipeline()
        assert p.camera_id == "CAM-GST-01"

    def test_frames_dropped_initially_zero(self):
        p = self._pipeline()
        assert p.frames_dropped == 0

    def test_start_and_stop(self):
        """Start then stop should not raise any exceptions."""
        p = self._pipeline()
        p.start()
        time.sleep(0.1)
        p.stop()
        assert p.status == PipelineStatus.STOPPED

    def test_read_returns_none_before_start(self):
        p = self._pipeline()
        result = p.read(timeout=0.01)
        assert result is None

    def test_gstreamer_availability_check(self):
        """_is_gstreamer_available() should return a bool without error."""
        result = _is_gstreamer_available()
        assert isinstance(result, bool)

    def test_gstreamer_string_override(self):
        """A custom gstreamer_string in config should override the default."""
        config = _make_cam_config()
        config["gstreamer_string"] = "fakesrc ! fakesink"
        p = GStreamerPipeline(config, "CAM-GST-02")
        assert p._gst_string == "fakesrc ! fakesink"

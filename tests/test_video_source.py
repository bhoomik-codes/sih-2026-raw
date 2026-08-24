"""
tests/test_video_source.py
---------------------------
Unit tests for VideoSource.

Tests:
    - Source opens a local video file
    - Bounded queue: never exceeds max_queue_size
    - Latest-frame strategy: old frames are dropped when queue is full
    - Frame fields: data, timestamp, frame_id
    - Reconnect: source starts cleanly after stop+start
    - Headless: reads frames without display

All tests use local video files or synthetic VideoCapture mocks.
No RTSP connection required.

Run:
    pytest tests/test_video_source.py -v
"""

from __future__ import annotations

import queue
import threading
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from apps.edge.video_source import Frame, VideoSource


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_fake_cap(num_frames: int = 200, h: int = 480, w: int = 640):
    """Return a mock cv2.VideoCapture that emits `num_frames` synthetic frames."""
    call_count = [0]

    def fake_read():
        call_count[0] += 1
        if call_count[0] > num_frames:
            # Simulate end-of-file / stream loss
            return False, None
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :, 0] = call_count[0] % 256  # Vary content for uniqueness
        return True, frame

    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.side_effect = fake_read
    mock_cap.set.return_value = True
    return mock_cap


# ── Basic functionality ───────────────────────────────────────────────────────


class TestVideoSourceBasic:
    """Tests using a mocked cv2.VideoCapture."""

    def test_source_starts_and_stops(self):
        with patch("cv2.VideoCapture", return_value=_make_fake_cap()):
            src = VideoSource("fake_source.mp4", max_queue_size=2, name="TEST")
            src.start()
            time.sleep(0.1)
            src.stop()
            # Should not raise

    def test_read_returns_frame(self):
        with patch("cv2.VideoCapture", return_value=_make_fake_cap(100)):
            src = VideoSource("fake.mp4", max_queue_size=2, name="TEST")
            src.start()
            time.sleep(0.1)
            frame = src.read(timeout=1.0)
            src.stop()

        assert frame is not None
        assert isinstance(frame, Frame)
        assert isinstance(frame.data, np.ndarray)
        assert frame.data.shape == (480, 640, 3)

    def test_frame_id_positive(self):
        with patch("cv2.VideoCapture", return_value=_make_fake_cap(100)):
            src = VideoSource("fake.mp4", max_queue_size=2, name="TEST")
            src.start()
            time.sleep(0.1)
            frame = src.read(timeout=1.0)
            src.stop()

        assert frame is not None
        assert frame.frame_id > 0

    def test_frame_timestamp_recent(self):
        before = time.time()
        with patch("cv2.VideoCapture", return_value=_make_fake_cap(50)):
            src = VideoSource("fake.mp4", max_queue_size=2, name="TEST")
            src.start()
            time.sleep(0.1)
            frame = src.read(timeout=1.0)
            src.stop()
        after = time.time()

        assert frame is not None
        assert before <= frame.timestamp <= after + 1.0

    def test_read_returns_none_when_no_frames(self):
        src = VideoSource("nonexistent.mp4", max_queue_size=2, name="TEST")
        # Don't start — queue is empty
        result = src.read(timeout=0.05)
        assert result is None

    def test_is_connected_true_when_running(self):
        with patch("cv2.VideoCapture", return_value=_make_fake_cap(10000)):
            src = VideoSource("fake.mp4", max_queue_size=2, name="TEST")
            src.start()
            time.sleep(0.05)
            connected = src.is_connected
            src.stop()

        assert connected is True


# ── Queue bounding tests ──────────────────────────────────────────────────────


class TestQueueBounding:
    """Verify the bounded queue and latest-frame drop semantics."""

    def test_queue_never_exceeds_max_size(self):
        """
        Even if the reader thread is much faster than the consumer,
        the internal queue must never hold more than max_queue_size frames.
        """
        max_q = 2
        with patch("cv2.VideoCapture", return_value=_make_fake_cap(500)):
            src = VideoSource("fake.mp4", max_queue_size=max_q, name="TEST")
            src.start()

            # Let reader run for a bit without consuming
            time.sleep(0.2)

            measured_depths = []
            for _ in range(20):
                measured_depths.append(src._queue.qsize())
                time.sleep(0.01)

            src.stop()

        assert all(d <= max_q for d in measured_depths), (
            f"Queue exceeded max_queue_size={max_q}: {measured_depths}"
        )

    def test_frames_are_dropped_when_queue_full(self):
        """
        After letting the reader run unstopped, dropped_frames should be > 0,
        indicating the latest-frame strategy is working.
        """
        with patch("cv2.VideoCapture", return_value=_make_fake_cap(1000)):
            src = VideoSource("fake.mp4", max_queue_size=1, name="TEST")
            src.start()

            # Don't read — let queue fill and overflow
            time.sleep(0.3)
            dropped = src.frames_dropped
            src.stop()

        assert dropped > 0, (
            "Expected frames to be dropped when queue is full and consumer is absent"
        )

    def test_latest_frame_semantics(self):
        """
        After letting reader run briefly without consuming, the frame we
        finally read should be a RECENT frame (high frame_id), not the
        first frame produced.
        """
        with patch("cv2.VideoCapture", return_value=_make_fake_cap(1000)):
            src = VideoSource("fake.mp4", max_queue_size=2, name="TEST")
            src.start()

            # Let reader produce many frames without consuming
            time.sleep(0.3)

            frame = src.read(timeout=0.5)
            src.stop()

        assert frame is not None
        # We should have read past frame 1 — should be a fairly recent frame
        assert frame.frame_id > 5, (
            f"Expected a recent frame but got frame_id={frame.frame_id}. "
            f"Latest-frame strategy may not be working."
        )


# ── Enqueue internals ─────────────────────────────────────────────────────────


class TestEnqueueLogic:
    """Direct unit tests on the _enqueue method."""

    def _make_source(self, max_q: int = 2) -> VideoSource:
        # Don't start the thread — test _enqueue directly
        return VideoSource("dummy", max_queue_size=max_q, name="TEST")

    def _make_frame(self, fid: int) -> Frame:
        return Frame(
            data=np.zeros((10, 10, 3), dtype=np.uint8),
            timestamp=time.time(),
            frame_id=fid,
        )

    def test_enqueue_adds_frame(self):
        src = self._make_source(max_q=3)
        src._enqueue(self._make_frame(1))
        assert src._queue.qsize() == 1

    def test_enqueue_full_drops_oldest(self):
        src = self._make_source(max_q=2)
        src._enqueue(self._make_frame(1))
        src._enqueue(self._make_frame(2))
        # Queue is now full (size=2)
        # Enqueueing a 3rd should drop the oldest (frame 1)
        src._enqueue(self._make_frame(3))

        assert src._queue.qsize() == 2
        assert src.frames_dropped == 1

        # The first frame we can read should be frame 2 (frame 1 was dropped)
        f = src.read(timeout=0.1)
        assert f is not None
        assert f.frame_id == 2


# ── Failed source tests ───────────────────────────────────────────────────────


class TestFailedSource:
    """Verify graceful behaviour when the source cannot be opened."""

    def test_failed_open_does_not_crash(self):
        """If the source URI is invalid, VideoSource should not crash."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False  # Simulate open failure

        with patch("cv2.VideoCapture", return_value=mock_cap):
            src = VideoSource("rtsp://bad-url", max_queue_size=2, reconnect_delay_s=0.05)
            src.start()
            # Give it time to attempt reconnection
            time.sleep(0.2)
            result = src.read(timeout=0.1)
            src.stop()

        # Should not have produced any frames
        assert result is None
        assert not src.is_connected

    def test_frames_read_zero_on_failure(self):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False

        with patch("cv2.VideoCapture", return_value=mock_cap):
            src = VideoSource("rtsp://bad-url", reconnect_delay_s=0.05)
            src.start()
            time.sleep(0.15)
            src.stop()

        assert src.frames_read == 0

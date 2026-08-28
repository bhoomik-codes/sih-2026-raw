"""
apps.edge.video_source
-----------------------
Thread-safe video source with bounded latest-frame strategy.

Key design decisions (from context §21 – Frame Queue Explosion):

1. LATEST-FRAME STRATEGY:
   The reader thread runs at camera speed (e.g. 30 FPS). The inference
   loop runs slower (e.g. 10 FPS). Instead of queuing all 30 frames,
   we keep only the most recent frame in a bounded queue of size `max_queue_size`.
   When the queue is full, the oldest frame is discarded.
   → The inference loop always processes the FRESHEST available frame.
   → No latency build-up. No stale frames. True real-time behaviour.

2. RTSP WATCHDOG:
   Cameras can drop, freeze, or send corrupt frames. The reader thread
   detects failures and automatically reconnects after `reconnect_delay_s` seconds.
   The main inference loop is never blocked by camera failures.

3. FRAME NAMEDTUPLE:
   Each frame carries its capture timestamp and a monotonically increasing
   frame_id. This allows the event engine (Phase 3+) to reason about time.

Usage:
    source = VideoSource("rtsp://192.168.1.10:554/stream", max_queue_size=2)
    source.start()
    while True:
        frame = source.read()
        if frame is not None:
            process(frame.data)
    source.stop()
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections import namedtuple
from typing import Optional

import cv2

logger = logging.getLogger(__name__)

# Each frame produced by VideoSource.
# data:     BGR numpy array (H, W, 3)
# timestamp: Unix time (seconds) when the frame was captured by the reader thread
# frame_id:  Monotonically increasing counter (not the camera's internal PTS)
Frame = namedtuple("Frame", ["data", "timestamp", "frame_id"])


class VideoSource:
    """
    Thread-safe video source that reads from a local file or RTSP stream.

    The reader thread continuously reads frames from the source and places
    them in a bounded queue. When the queue is full, the oldest frame is
    removed (drop-oldest strategy) and the new frame is enqueued.

    Args:
        source_uri:        Path to a video file, or an RTSP/HTTP stream URL.
                           Also accepts an integer (webcam device index).
        max_queue_size:    Maximum frames held in the queue. Keep this small
                           (1–3) to ensure low latency. Default: 2.
        reconnect_delay_s: Seconds to wait before reconnecting on stream loss.
                           Default: 3.0.
        name:              Human-readable name for this camera (used in logs).
    """

    def __init__(
        self,
        source_uri: str | int,
        max_queue_size: int = 2,
        reconnect_delay_s: float = 3.0,
        read_timeout_s: float = 5.0,
        name: str = "CAM-01",
    ) -> None:
        self._uri = source_uri
        self._max_queue_size = max(1, max_queue_size)
        self._reconnect_delay_s = reconnect_delay_s
        self._read_timeout_s = read_timeout_s
        self._name = name
        self._is_network_source = isinstance(source_uri, str) and (
            source_uri.startswith("rtsp://")
            or source_uri.startswith("http://")
            or source_uri.startswith("https://")
        )

        self._queue: queue.Queue[Frame] = queue.Queue(maxsize=self._max_queue_size)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Statistics and health tracking
        self._frames_read: int = 0
        self._frames_dropped: int = 0
        self._is_connected: bool = False
        self._last_frame_ts: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> "VideoSource":
        """Start the background reader thread. Returns self for chaining."""
        if self._thread and self._thread.is_alive():
            logger.warning("[%s] VideoSource already running.", self._name)
            return self

        self._stop_event.clear()
        self._last_frame_ts = time.time()
        self._thread = threading.Thread(
            target=self._reader_loop,
            name=f"VideoSource-{self._name}",
            daemon=True,
        )
        self._thread.start()
        logger.info("[%s] VideoSource started  source=%s", self._name, self._uri)
        return self

    def stop(self) -> None:
        """Signal the reader thread to stop and wait for it to finish."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info(
            "[%s] VideoSource stopped  frames_read=%d  frames_dropped=%d",
            self._name,
            self._frames_read,
            self._frames_dropped,
        )

    def read(self, timeout: float = 0.0) -> Optional[Frame]:
        """
        Get the most recent frame from the queue (non-blocking when timeout <= 0).

        Returns None if no frame is available within the timeout.

        Args:
            timeout: Maximum seconds to wait (default 0.0 for non-blocking).

        Returns:
            Frame namedtuple, or None.
        """
        try:
            if timeout <= 0.0:
                return self._queue.get_nowait()
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def is_connected(self) -> bool:
        """True if the underlying video source is currently open."""
        return self._is_connected

    @property
    def name(self) -> str:
        return self._name

    @property
    def frames_read(self) -> int:
        return self._frames_read

    @property
    def frames_dropped(self) -> int:
        return self._frames_dropped

    def __repr__(self) -> str:
        return f"VideoSource(name={self._name!r} uri={self._uri!r} connected={self._is_connected})"

    # ------------------------------------------------------------------
    # Internal reader thread
    # ------------------------------------------------------------------

    def _reader_loop(self) -> None:
        """
        Background thread: continuously reads frames from the source.

        On failure: waits `reconnect_delay_s` seconds and retries.
        On stop: releases the OpenCV capture and exits cleanly.
        """
        while not self._stop_event.is_set():
            cap = self._open_source()
            if cap is None:
                # Could not open — wait before retrying
                self._is_connected = False
                self._stop_event.wait(self._reconnect_delay_s)
                continue

            self._is_connected = True
            self._last_frame_ts = time.time()
            logger.info("[%s] Stream opened successfully.", self._name)

            try:
                self._read_frames(cap)
            finally:
                try:
                    cap.release()
                except Exception:
                    pass
                self._is_connected = False
                logger.info("[%s] Stream closed.", self._name)

            if not self._stop_event.is_set():
                logger.warning(
                    "[%s] Stream lost. Reconnecting in %.1fs...",
                    self._name,
                    self._reconnect_delay_s,
                )
                self._stop_event.wait(self._reconnect_delay_s)


    def _open_source(self) -> Optional[cv2.VideoCapture]:
        """
        Open the video source and return a cv2.VideoCapture on success.

        Returns None if the source cannot be opened.
        """
        try:
            cap = cv2.VideoCapture(self._uri)
        except Exception as exc:
            logger.error("[%s] cv2.VideoCapture raised: %s", self._name, exc)
            return None

        if not cap.isOpened():
            logger.error("[%s] Failed to open source: %s", self._name, self._uri)
            return None

        # For RTSP: set buffer size to 1 to minimise capture-side latency
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        try:
            # Set timeouts where supported by OpenCV backend
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
        except Exception:
            pass
        return cap

    def _read_frames(self, cap: cv2.VideoCapture) -> None:
        """
        Inner loop: read frames from an open capture and enqueue them.

        Exits when stop is requested or the capture becomes unavailable.
        """
        while not self._stop_event.is_set():
            try:
                ret, data = cap.read()
            except Exception as e:
                logger.warning("[%s] cap.read() exception: %s", self._name, e)
                break

            if not ret or data is None or data.size == 0:
                logger.warning("[%s] cap.read() returned invalid frame.", self._name)
                break  # Triggers reconnect in outer loop

            now = time.time()
            self._last_frame_ts = now
            self._frames_read += 1
            frame = Frame(
                data=data,
                timestamp=now,
                frame_id=self._frames_read,
            )
            self._enqueue(frame)

    def _enqueue(self, frame: Frame) -> None:
        """
        Enqueue a frame using the LATEST-FRAME strategy.

        If the queue is full, drop the oldest frame (which is stale)
        and insert the new one (which is current).

        This ensures the inference loop always sees the most recent frame,
        even when it runs slower than the camera.
        """
        if self._queue.full():
            try:
                self._queue.get_nowait()  # discard oldest
                self._frames_dropped += 1
            except queue.Empty:
                pass  # race condition: another consumer drained it — fine

        try:
            self._queue.put_nowait(frame)
        except queue.Full:
            # Extremely rare — another producer beat us. Drop this frame.
            self._frames_dropped += 1

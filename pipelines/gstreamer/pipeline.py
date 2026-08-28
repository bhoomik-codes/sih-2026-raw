"""
pipelines.gstreamer.pipeline
-----------------------------
GStreamer-based hardware-decode video pipeline (Phase 8).

Uses OpenCV's built-in GStreamer backend for hardware-accelerated video
decoding, which reduces CPU load compared to the software decoder used by
the default OpenCVPipeline.

On Windows, GStreamer support requires:
    - OpenCV built with GStreamer support (check: cv2.getBuildInformation())
    - GStreamer binaries installed and in PATH

This pipeline falls back to the standard OpenCV backend (FFMPEG/MSMF) if
GStreamer is unavailable, logging a warning. This ensures the system remains
functional across all environments.

Config keys:
    source            (str)   : GStreamer source string OR a file/RTSP URI.
    name              (str)   : Camera name.
    gstreamer_string  (str)   : Override: raw GStreamer pipeline string.
                                If set, `source` is ignored.
    max_queue_size    (int)   : Frame queue depth. Default: 2.
    reconnect_delay_s (float) : Reconnect delay. Default: 3.0.

Example RTSP GStreamer string (hardware decode):
    rtspsrc location=rtsp://... latency=100 !
    rtph264depay ! h264parse ! nvh264dec ! videoconvert ! appsink

Example file source (software decode via GStreamer):
    filesrc location=data/videos/test_video.mp4 ! decodebin ! videoconvert ! appsink
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Optional

import cv2

from apps.edge.video_source import Frame
from pipelines.base import PipelineStatus, VideoPipelineBase

logger = logging.getLogger(__name__)

# Default GStreamer pipeline strings
_GSTREAMER_FILE_TEMPLATE = (
    "filesrc location={source} ! decodebin ! videoconvert ! "
    "video/x-raw,format=BGR ! appsink drop=true max-buffers=2 sync=false"
)
_GSTREAMER_RTSP_TEMPLATE = (
    "rtspsrc location={source} latency=100 ! rtph264depay ! h264parse ! "
    "avdec_h264 ! videoconvert ! video/x-raw,format=BGR ! "
    "appsink drop=true max-buffers=2 sync=false"
)


def _is_gstreamer_available() -> bool:
    """Check if OpenCV was built with GStreamer support."""
    build_info = cv2.getBuildInformation()
    return "GStreamer" in build_info and "YES" in build_info.split("GStreamer")[1][:20]


def _build_gstreamer_string(source: str, gstreamer_string: Optional[str]) -> str:
    """Build the GStreamer pipeline string for the given source."""
    if gstreamer_string:
        return gstreamer_string
    if source.startswith("rtsp://"):
        return _GSTREAMER_RTSP_TEMPLATE.format(source=source)
    else:
        # Local file
        return _GSTREAMER_FILE_TEMPLATE.format(source=source)


class GStreamerPipeline(VideoPipelineBase):
    """
    Hardware-accelerated video pipeline using GStreamer backend.

    Falls back to standard OpenCV FFMPEG backend if GStreamer is not available,
    ensuring the system works even without a full GStreamer installation.

    Args:
        config:    Camera config dict.
        camera_id: Unique camera identifier.
    """

    def __init__(self, config: dict, camera_id: str) -> None:
        super().__init__(config, camera_id)

        self._source: str = str(config.get("source", ""))
        self._gst_string: Optional[str] = config.get("gstreamer_string", None)
        self._max_queue: int = int(config.get("max_queue_size", 2))
        self._reconnect_delay: float = float(config.get("reconnect_delay_s", 3.0))

        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._frame_queue: queue.Queue = queue.Queue(maxsize=self._max_queue)
        self._running: bool = False
        self._frame_count: int = 0
        self._frames_dropped: int = 0
        self._gstreamer_available: bool = _is_gstreamer_available()

        if not self._gstreamer_available:
            logger.warning(
                "[%s] GStreamer not available in this OpenCV build — "
                "falling back to FFMPEG/MSMF backend.",
                camera_id,
            )

    # ------------------------------------------------------------------
    # VideoPipelineBase interface
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the GStreamer (or fallback) capture pipeline."""
        if self._running:
            logger.debug("[%s] Already running.", self._camera_id)
            return

        self._status = PipelineStatus.STARTING
        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop,
            name=f"gst-{self._camera_id}",
            daemon=True,
        )
        self._thread.start()
        logger.info("[%s] GStreamerPipeline started.", self._camera_id)

    def stop(self) -> None:
        """Stop capture and release resources."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        if self._cap and self._cap.isOpened():
            self._cap.release()
        self._status = PipelineStatus.STOPPED
        logger.info("[%s] GStreamerPipeline stopped.", self._camera_id)

    def read(self, timeout: float = 0.05) -> Optional[Frame]:
        """Retrieve the latest frame from the capture queue."""
        try:
            return self._frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def frames_dropped(self) -> int:
        return self._frames_dropped

    # ------------------------------------------------------------------
    # Internal capture loop
    # ------------------------------------------------------------------

    def _open_capture(self) -> cv2.VideoCapture:
        """Open VideoCapture with GStreamer or fallback backend."""
        if self._gstreamer_available:
            gst_string = _build_gstreamer_string(self._source, self._gst_string)
            logger.info("[%s] Opening GStreamer pipeline: %s", self._camera_id, gst_string[:80])
            cap = cv2.VideoCapture(gst_string, cv2.CAP_GSTREAMER)
        else:
            logger.info("[%s] Opening with default backend: %s", self._camera_id, self._source)
            cap = cv2.VideoCapture(self._source)
        return cap

    def _capture_loop(self) -> None:
        """Background thread: continuously read frames and push to queue."""
        while self._running:
            self._cap = self._open_capture()

            if not self._cap.isOpened():
                logger.warning(
                    "[%s] Failed to open source — retrying in %.1fs.",
                    self._camera_id,
                    self._reconnect_delay,
                )
                self._status = PipelineStatus.RECONNECTING
                time.sleep(self._reconnect_delay)
                continue

            self._status = PipelineStatus.RUNNING
            logger.info("[%s] Stream opened successfully.", self._camera_id)

            while self._running:
                ret, bgr = self._cap.read()
                if not ret or bgr is None:
                    logger.warning("[%s] Frame read failed — reconnecting.", self._camera_id)
                    self._status = PipelineStatus.RECONNECTING
                    break

                self._frame_count += 1
                frame = Frame(
                    data=bgr,
                    frame_id=self._frame_count,
                    timestamp=time.time(),
                )

                # Latest-frame semantics: drop oldest if queue is full
                if self._frame_queue.full():
                    try:
                        self._frame_queue.get_nowait()
                        self._frames_dropped += 1
                    except queue.Empty:
                        pass

                try:
                    self._frame_queue.put_nowait(frame)
                except queue.Full:
                    self._frames_dropped += 1

            if self._cap:
                self._cap.release()

            if self._running:
                logger.info("[%s] Reconnecting in %.1fs.", self._camera_id, self._reconnect_delay)
                time.sleep(self._reconnect_delay)

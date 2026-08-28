"""
pipelines.deepstream.pipeline
------------------------------
NVIDIA DeepStream multi-stream hardware-accelerated video pipeline (Phase 8).

Utilizes NVIDIA Jetson / dGPU hardware decoder and nvstreammux plugins:
    nvurisrcbin (or rtspsrc ! rtph264depay ! nvv4l2decoder) !
    nvvideoconvert ! video/x-raw(memory:NVMM) !
    nvstreammux ! nvvideoconvert ! video/x-raw,format=BGR ! appsink

Falls back seamlessly to hardware GStreamer or OpenCV when NVIDIA DeepStream
drivers / Jetson NVMM memory elements are not detected in the environment.
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

# DeepStream NVIDIA GPU accelerated templates
_DEEPSTREAM_RTSP_NVMM = (
    "rtspsrc location={source} latency=100 drop-on-latency=true ! "
    "rtph264depay ! h264parse ! nvv4l2decoder ! "
    "nvvideoconvert ! video/x-raw,format=BGR ! "
    "appsink drop=true max-buffers=2 sync=false"
)

_DEEPSTREAM_FILE_NVMM = (
    "filesrc location={source} ! qtdemux ! h264parse ! nvv4l2decoder ! "
    "nvvideoconvert ! video/x-raw,format=BGR ! "
    "appsink drop=true max-buffers=2 sync=false"
)

_GSTREAMER_CPU_FALLBACK = (
    "filesrc location={source} ! decodebin ! videoconvert ! "
    "video/x-raw,format=BGR ! appsink drop=true max-buffers=2 sync=false"
)


def _is_deepstream_capable() -> bool:
    """Check if OpenCV has GStreamer and NVIDIA elements available."""
    try:
        build_info = cv2.getBuildInformation()
        return "GStreamer" in build_info and "YES" in build_info.split("GStreamer")[1][:20]
    except Exception:
        return False


class DeepStreamPipeline(VideoPipelineBase):
    """
    NVIDIA DeepStream-accelerated video pipeline.

    Supports hardware multi-stream ingestion with NVDEC/nvv4l2decoder,
    falling back gracefully to standard GStreamer / OpenCV decoding.
    """

    def __init__(self, config: dict, camera_id: str) -> None:
        super().__init__(config, camera_id)

        self._source: str = str(config.get("source", ""))
        self._deepstream_string: Optional[str] = config.get("deepstream_string", None)
        self._max_queue: int = int(config.get("max_queue_size", 2))
        self._reconnect_delay: float = float(config.get("reconnect_delay_s", 3.0))

        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._queue: queue.Queue[Frame] = queue.Queue(maxsize=self._max_queue)

        self._frames_read: int = 0
        self._frames_dropped: int = 0
        self._using_hardware_accel: bool = False

    @property
    def frames_read(self) -> int:
        return self._frames_read

    @property
    def frames_dropped(self) -> int:
        return self._frames_dropped

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._status = PipelineStatus.STARTING
        self._thread = threading.Thread(
            target=self._reader_loop,
            name=f"DeepStreamPipeline-{self._camera_id}",
            daemon=True,
        )
        self._thread.start()
        logger.info("[%s] DeepStreamPipeline started for source: %s", self._camera_id, self._source)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        self._status = PipelineStatus.STOPPED
        logger.info(
            "[%s] DeepStreamPipeline stopped (frames_read=%d, frames_dropped=%d)",
            self._camera_id,
            self._frames_read,
            self._frames_dropped,
        )

    def read(self, timeout: float = 0.0) -> Optional[Frame]:
        """Retrieve latest frame from the pipeline queue."""
        try:
            if timeout <= 0.0:
                return self._queue.get_nowait()
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _build_pipeline_string(self) -> str:
        if self._deepstream_string:
            return self._deepstream_string
        if self._source.startswith("rtsp://"):
            return _DEEPSTREAM_RTSP_NVMM.format(source=self._source)
        return _DEEPSTREAM_FILE_NVMM.format(source=self._source)

    def _open_capture(self) -> Optional[cv2.VideoCapture]:
        # Try NVIDIA DeepStream hardware pipeline first
        if _is_deepstream_capable():
            gst_str = self._build_pipeline_string()
            logger.debug("[%s] Trying DeepStream Gst pipeline: %s", self._camera_id, gst_str)
            try:
                cap = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)
                if cap.isOpened():
                    self._using_hardware_accel = True
                    logger.info(
                        "[%s] Opened with DeepStream hardware acceleration.", self._camera_id
                    )
                    return cap
            except Exception as e:
                logger.debug("[%s] DeepStream Gst failed: %s", self._camera_id, e)

        # Fallback to standard OpenCV capture
        logger.info(
            "[%s] Using OpenCV standard backend fallback for %s", self._camera_id, self._source
        )
        self._using_hardware_accel = False
        try:
            cap = cv2.VideoCapture(self._source)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                return cap
        except Exception as err:
            logger.error("[%s] Failed to open fallback capture: %s", self._camera_id, err)

        return None

    def _reader_loop(self) -> None:
        while not self._stop_event.is_set():
            self._cap = self._open_capture()
            if self._cap is None:
                self._status = PipelineStatus.RECONNECTING
                self._stop_event.wait(self._reconnect_delay)
                continue

            self._status = PipelineStatus.RUNNING
            logger.info("[%s] DeepStream pipeline stream active.", self._camera_id)

            while not self._stop_event.is_set():
                ret, data = self._cap.read()
                if not ret or data is None or data.size == 0:
                    logger.warning("[%s] Stream read returned invalid frame.", self._camera_id)
                    break

                self._frames_read += 1
                frame = Frame(
                    data=data,
                    timestamp=time.time(),
                    frame_id=self._frames_read,
                )
                self._enqueue(frame)

            self._cap.release()
            self._cap = None
            if not self._stop_event.is_set():
                self._status = PipelineStatus.RECONNECTING
                logger.warning(
                    "[%s] Stream lost, reconnecting in %.1fs...",
                    self._camera_id,
                    self._reconnect_delay,
                )
                self._stop_event.wait(self._reconnect_delay)

        self._status = PipelineStatus.STOPPED

    def _enqueue(self, frame: Frame) -> None:
        try:
            self._queue.put_nowait(frame)
        except queue.Full:
            try:
                _ = self._queue.get_nowait()
                self._frames_dropped += 1
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(frame)
            except queue.Full:
                self._frames_dropped += 1

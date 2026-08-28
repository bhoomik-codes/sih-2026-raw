"""
pipelines.opencv.pipeline
--------------------------
OpenCV-based video pipeline (Phase 8).

Wraps the existing VideoSource into the new VideoPipelineBase interface,
enabling it to be managed by the MultiCameraManager alongside other backends.

This is the default pipeline backend for Windows (where GStreamer and
DeepStream may not be fully available).

Config keys (from each entry in the YAML ``cameras`` list):
    source           (str)   : Video source URI (file path, RTSP URL, etc.)
    name             (str)   : Human-readable camera name.
    max_queue_size   (int)   : Frame queue depth. Default: 2.
    reconnect_delay_s (float): Delay between reconnection attempts. Default: 3.0.
"""

from __future__ import annotations

import logging
from typing import Optional

from apps.edge.video_source import Frame, VideoSource
from pipelines.base import PipelineStatus, VideoPipelineBase

logger = logging.getLogger(__name__)


class OpenCVPipeline(VideoPipelineBase):
    """
    OpenCV VideoCapture-based pipeline using the existing VideoSource backend.

    This is the production-ready default pipeline for Phase 8. It wraps
    VideoSource (which already handles frame queuing, dropped-frame tracking,
    and thread-safe access) and presents the unified VideoPipelineBase interface.

    Args:
        config:    Camera config dict from the ``cameras`` YAML list.
        camera_id: Unique camera identifier (e.g. "BOP-CAM-01").
    """

    def __init__(self, config: dict, camera_id: str) -> None:
        super().__init__(config, camera_id)

        source_uri = config.get("source", 0)
        max_queue_size = int(config.get("max_queue_size", 2))
        reconnect_delay = float(config.get("reconnect_delay_s", 3.0))
        cam_name = config.get("name", camera_id)

        self._video_source = VideoSource(
            source_uri=source_uri,
            max_queue_size=max_queue_size,
            reconnect_delay_s=reconnect_delay,
            name=cam_name,
        )

    # ------------------------------------------------------------------
    # VideoPipelineBase interface
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the underlying VideoSource thread."""
        if self._status == PipelineStatus.RUNNING:
            logger.debug("[%s] Already running — ignoring start().", self._camera_id)
            return
        self._status = PipelineStatus.STARTING
        self._video_source.start()
        self._status = PipelineStatus.RUNNING
        logger.info("[%s] OpenCVPipeline started.", self._camera_id)

    def stop(self) -> None:
        """Stop the underlying VideoSource thread and release resources."""
        self._video_source.stop()
        self._status = PipelineStatus.STOPPED
        logger.info("[%s] OpenCVPipeline stopped.", self._camera_id)

    def read(self, timeout: float = 0.05) -> Optional[Frame]:
        """
        Retrieve the latest frame from the VideoSource queue.

        Args:
            timeout: Maximum wait time in seconds.

        Returns:
            Frame or None.
        """
        return self._video_source.read(timeout=timeout)

    # ------------------------------------------------------------------
    # Additional properties
    # ------------------------------------------------------------------

    @property
    def frames_dropped(self) -> int:
        """Number of frames dropped since pipeline started."""
        return self._video_source.frames_dropped

    @property
    def is_connected(self) -> bool:
        """True if the VideoSource reports a live connection."""
        return self._video_source.is_connected

"""
apps.edge.multi_camera_manager
--------------------------------
MultiCameraManager — manages N video pipelines concurrently (Phase 8).

Each camera runs in its own pipeline (OpenCVPipeline or GStreamerPipeline)
and is managed by this class. The EdgeProcessor (or a future multi-stream
version) calls get_latest_frames() to get the most recent frame from each
active camera.

Design principles:
    - One pipeline per camera, each with its own thread.
    - Health tracking: ONLINE / OFFLINE / RECONNECTING per camera.
    - No shared state between camera pipelines.
    - Thread-safe access to camera status and frames.

Usage (from YAML config):
    cameras:
      - id: "BOP-CAM-01"
        source: "data/videos/test_video.mp4"
        name: "Border Camera East"
        pipeline: "opencv"      # or "gstreamer"
      - id: "BOP-CAM-02"
        source: "rtsp://192.168.1.10/stream1"
        name: "Border Camera West"
        pipeline: "gstreamer"
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Dict, List, Optional

from apps.edge.video_source import Frame
from pipelines.base import PipelineStatus, VideoPipelineBase

logger = logging.getLogger(__name__)


def _create_pipeline(cam_cfg: dict, camera_id: str) -> VideoPipelineBase:
    """
    Factory: create the appropriate pipeline backend for a camera config.

    Args:
        cam_cfg:   Camera config dict from YAML (one entry from ``cameras`` list).
        camera_id: Unique camera identifier.

    Returns:
        An instantiated (but not yet started) VideoPipelineBase subclass.
    """
    backend = cam_cfg.get("pipeline", "opencv").lower()
    if backend == "gstreamer":
        from pipelines.gstreamer.pipeline import GStreamerPipeline
        return GStreamerPipeline(cam_cfg, camera_id)
    else:
        from pipelines.opencv.pipeline import OpenCVPipeline
        return OpenCVPipeline(cam_cfg, camera_id)


class CameraHealthRecord:
    """Tracks the health of a single camera pipeline."""

    def __init__(self, camera_id: str) -> None:
        self.camera_id = camera_id
        self.status: PipelineStatus = PipelineStatus.IDLE
        self.frames_received: int = 0
        self.frames_dropped: int = 0
        self.last_frame_ts: float = 0.0
        self.started_at: float = 0.0

    @property
    def fps_estimate(self) -> float:
        """Rough FPS estimate based on elapsed time and received frames."""
        elapsed = time.time() - self.started_at
        if elapsed <= 0:
            return 0.0
        return self.frames_received / elapsed

    def __repr__(self) -> str:
        return (
            f"CameraHealthRecord(id={self.camera_id!r}, status={self.status.name}, "
            f"frames={self.frames_received}, fps~{self.fps_estimate:.1f})"
        )


class MultiCameraManager:
    """
    Manages multiple concurrent video pipelines for multi-camera surveillance.

    Each pipeline runs in its own background thread. This class provides a
    unified interface for starting/stopping all cameras and retrieving the
    latest available frame from any camera.

    Args:
        cameras_config: List of camera config dicts (from YAML ``cameras`` key).
    """

    def __init__(self, cameras_config: List[dict]) -> None:
        self._pipelines: Dict[str, VideoPipelineBase] = {}
        self._health: Dict[str, CameraHealthRecord] = {}
        self._lock = threading.Lock()

        for cam_cfg in cameras_config:
            camera_id = cam_cfg.get("id", cam_cfg.get("name", f"CAM-{len(self._pipelines):02d}"))
            pipeline = _create_pipeline(cam_cfg, camera_id)
            self._pipelines[camera_id] = pipeline
            self._health[camera_id] = CameraHealthRecord(camera_id)
            logger.info(
                "Registered camera: %s  backend=%s  source=%s",
                camera_id,
                cam_cfg.get("pipeline", "opencv"),
                cam_cfg.get("source", "?"),
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_all(self) -> None:
        """Start all registered camera pipelines."""
        for camera_id, pipeline in self._pipelines.items():
            try:
                pipeline.start()
                with self._lock:
                    self._health[camera_id].started_at = time.time()
                    self._health[camera_id].status = PipelineStatus.RUNNING
                logger.info("Started pipeline: %s", camera_id)
            except Exception as exc:
                logger.error("Failed to start %s: %s", camera_id, exc)
                with self._lock:
                    self._health[camera_id].status = PipelineStatus.ERROR

    def stop_all(self) -> None:
        """Stop all registered camera pipelines."""
        for camera_id, pipeline in self._pipelines.items():
            try:
                pipeline.stop()
                with self._lock:
                    self._health[camera_id].status = PipelineStatus.STOPPED
                logger.info("Stopped pipeline: %s", camera_id)
            except Exception as exc:
                logger.error("Error stopping %s: %s", camera_id, exc)

    def start(self, camera_id: str) -> None:
        """Start a specific camera by ID."""
        if camera_id not in self._pipelines:
            raise KeyError(f"Camera not registered: {camera_id}")
        self._pipelines[camera_id].start()
        with self._lock:
            self._health[camera_id].started_at = time.time()
            self._health[camera_id].status = PipelineStatus.RUNNING

    def stop(self, camera_id: str) -> None:
        """Stop a specific camera by ID."""
        if camera_id not in self._pipelines:
            raise KeyError(f"Camera not registered: {camera_id}")
        self._pipelines[camera_id].stop()
        with self._lock:
            self._health[camera_id].status = PipelineStatus.STOPPED

    # ------------------------------------------------------------------
    # Frame access
    # ------------------------------------------------------------------

    def read(self, camera_id: str, timeout: float = 0.05) -> Optional[Frame]:
        """
        Retrieve the latest frame from a specific camera.

        Args:
            camera_id: Camera identifier.
            timeout:   Maximum wait time in seconds.

        Returns:
            Frame or None if no frame available within timeout.
        """
        if camera_id not in self._pipelines:
            return None
        frame = self._pipelines[camera_id].read(timeout=timeout)
        if frame is not None:
            with self._lock:
                self._health[camera_id].frames_received += 1
                self._health[camera_id].last_frame_ts = frame.timestamp
        return frame

    def get_latest_frames(self, timeout: float = 0.05) -> Dict[str, Optional[Frame]]:
        """
        Retrieve the latest available frame from ALL cameras.

        Args:
            timeout: Maximum wait per camera, in seconds.

        Returns:
            Dict mapping camera_id → Frame (or None if no frame available).
        """
        frames: Dict[str, Optional[Frame]] = {}
        for camera_id in self._pipelines:
            frames[camera_id] = self.read(camera_id, timeout=timeout)
        return frames

    # ------------------------------------------------------------------
    # Health / Status
    # ------------------------------------------------------------------

    @property
    def camera_ids(self) -> List[str]:
        """List of registered camera IDs."""
        return list(self._pipelines.keys())

    @property
    def num_cameras(self) -> int:
        """Number of registered cameras."""
        return len(self._pipelines)

    def get_health(self, camera_id: str) -> Optional[CameraHealthRecord]:
        """Get the health record for a specific camera."""
        return self._health.get(camera_id)

    def get_all_health(self) -> Dict[str, CameraHealthRecord]:
        """Get health records for all cameras."""
        with self._lock:
            return dict(self._health)

    def print_status(self) -> None:
        """Print a formatted status table to the logger."""
        logger.info("=" * 60)
        logger.info("MULTI-CAMERA STATUS  (%d cameras)", len(self._pipelines))
        logger.info("-" * 60)
        for cam_id, health in self._health.items():
            pipeline = self._pipelines[cam_id]
            dropped = getattr(pipeline, "frames_dropped", 0)
            logger.info(
                "  %-20s  %-12s  frames=%-6d  fps=%.1f  drop=%d",
                cam_id,
                health.status.name,
                health.frames_received,
                health.fps_estimate,
                dropped,
            )
        logger.info("=" * 60)

    def __len__(self) -> int:
        return len(self._pipelines)

    def __repr__(self) -> str:
        return f"MultiCameraManager(cameras={list(self._pipelines.keys())!r})"

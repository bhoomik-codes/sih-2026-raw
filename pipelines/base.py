"""
pipelines.base
---------------
Abstract base class for all video pipeline backends (Phase 8).

The pipeline abstraction allows the edge processor to work with any video
source: OpenCV, GStreamer, or (in future) DeepStream — without changing the
EdgeProcessor code.

Pipeline lifecycle:
    pipeline = OpenCVPipeline(config, camera_id)
    pipeline.start()
    frame = pipeline.read(timeout=0.05)
    pipeline.stop()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Optional

from apps.edge.video_source import Frame


class PipelineStatus(Enum):
    """Lifecycle state of a video pipeline."""

    IDLE = auto()  # Not yet started
    STARTING = auto()  # Connection in progress
    RUNNING = auto()  # Actively receiving frames
    RECONNECTING = auto()  # Temporarily disconnected, retrying
    STOPPED = auto()  # Cleanly shut down
    ERROR = auto()  # Unrecoverable error


class VideoPipelineBase(ABC):
    """
    Abstract base class for IBVAP video pipeline backends.

    Subclasses implement the actual video capture mechanism (OpenCV, GStreamer,
    DeepStream, etc.) while presenting a uniform interface to the rest of the
    system.

    All subclasses must:
        - Be thread-safe (start() and read() may be called from different threads).
        - Not block indefinitely in read() — always respect the timeout parameter.
        - Set self._status appropriately throughout the lifecycle.
        - Implement camera reconnection logic internally (RTSP watchdog).
    """

    def __init__(self, config: dict, camera_id: str) -> None:
        """
        Args:
            config:    Full camera config dict (the entry from the ``cameras`` list).
            camera_id: Unique identifier for this camera (e.g. "BOP-CAM-01").
        """
        self._config = config
        self._camera_id = camera_id
        self._status: PipelineStatus = PipelineStatus.IDLE

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def camera_id(self) -> str:
        """Unique camera identifier."""
        return self._camera_id

    @property
    def name(self) -> str:
        """Human-readable camera name (defaults to camera_id)."""
        return self._config.get("name", self._camera_id)

    @property
    def status(self) -> PipelineStatus:
        """Current pipeline lifecycle state."""
        return self._status

    @property
    def is_running(self) -> bool:
        """True if the pipeline is actively receiving frames."""
        return self._status == PipelineStatus.RUNNING

    # ------------------------------------------------------------------
    # Abstract interface — must be implemented by subclasses
    # ------------------------------------------------------------------

    @abstractmethod
    def start(self) -> None:
        """
        Start the video pipeline.

        Opens the video source, starts background threads / GStreamer pipeline.
        Must be idempotent (calling start() on an already-running pipeline is safe).
        """

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the video pipeline and release all resources.

        Must be safe to call even if the pipeline never started or already stopped.
        """

    @abstractmethod
    def read(self, timeout: float = 0.05) -> Optional[Frame]:
        """
        Retrieve the latest available frame.

        Args:
            timeout: Maximum time to wait for a frame, in seconds.

        Returns:
            A Frame dataclass, or None if no frame is available within timeout.
        """

    # ------------------------------------------------------------------
    # Optional hook — override in subclasses if needed
    # ------------------------------------------------------------------

    @property
    def frames_dropped(self) -> int:
        """Number of frames dropped since pipeline started. Override if tracked."""
        return 0

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(camera_id={self._camera_id!r}, status={self._status.name})"
        )

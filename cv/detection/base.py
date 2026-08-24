"""
cv.detection.base
-----------------
Abstract base class and core data contract for all detectors.

Rules:
- DetectorBase defines the interface every detector must implement.
- Detection is a plain dataclass — no model-specific fields.
- All downstream code (tracker, event engine) only consumes List[Detection].
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class BBox:
    """
    Axis-aligned bounding box in pixel coordinates.

    Origin is top-left of the frame.

    Attributes:
        x1: Left edge (pixels)
        y1: Top edge (pixels)
        x2: Right edge (pixels)
        y2: Bottom edge (pixels)
    """

    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def bottom_center(self) -> tuple[float, float]:
        """Bottom-center point — useful for virtual fence foot-point checks."""
        return ((self.x1 + self.x2) / 2.0, self.y2)

    def as_xyxy(self) -> tuple[float, float, float, float]:
        return (self.x1, self.y1, self.x2, self.y2)

    def as_xywh(self) -> tuple[float, float, float, float]:
        return (self.x1, self.y1, self.width, self.height)


@dataclass
class Detection:
    """
    Normalized output of any detector.

    All downstream code (tracker, event engine, risk engine) consumes
    this type. No YOLO-specific, ONNX-specific, or TensorRT-specific
    types appear outside this module.

    Attributes:
        bbox:        Bounding box in pixel coordinates.
        class_id:   COCO class ID (0=person, 2=car, 3=motorcycle, 5=bus, 7=truck).
        class_name: Human-readable class name (e.g. "person").
        confidence: Detector confidence score [0.0, 1.0].
        frame_id:   Sequential frame number within the current run.
        timestamp:  Unix timestamp (seconds) when the frame was captured.
        track_id:   Populated by the tracker in Phase 2 (None in Phase 1).
        meta:       Optional dict for detector-specific extras (not used downstream).
    """

    bbox: BBox
    class_id: int
    class_name: str
    confidence: float
    frame_id: int
    timestamp: float = field(default_factory=time.time)
    track_id: Optional[int] = None
    meta: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        tid = f" track={self.track_id}" if self.track_id is not None else ""
        return (
            f"Detection({self.class_name} conf={self.confidence:.2f}"
            f" bbox=({self.bbox.x1:.0f},{self.bbox.y1:.0f}"
            f",{self.bbox.x2:.0f},{self.bbox.y2:.0f})"
            f"{tid} frame={self.frame_id})"
        )


class DetectorBase(ABC):
    """
    Abstract interface that every detector implementation must satisfy.

    Design contract:
    - load() must be called before detect().
    - detect() must return a List[Detection] (never raise on empty frames).
    - warmup() should run a dummy inference to pre-allocate GPU memory.
    - All model-specific setup (weights loading, engine building) happens
      inside load(), not in __init__, so construction is always cheap.
    """

    def __init__(self, config: dict) -> None:
        """
        Args:
            config: Dict of detector settings from YAML (device, thresholds, etc.)
        """
        self._config = config
        self._loaded: bool = False

    @abstractmethod
    def load(self) -> None:
        """Load model weights and prepare for inference."""
        ...

    @abstractmethod
    def detect(self, frame, frame_id: int = 0) -> List[Detection]:
        """
        Run inference on a single BGR frame (numpy array).

        Args:
            frame:    BGR numpy array (H, W, 3).
            frame_id: Caller-assigned sequential frame number.

        Returns:
            List of Detection objects. Empty list if nothing detected.
        """
        ...

    def warmup(self, frame_shape: tuple[int, int, int] = (640, 640, 3)) -> None:
        """
        Run a dummy inference to pre-allocate GPU memory and JIT-compile kernels.

        Call this once after load() before the real inference loop.

        Args:
            frame_shape: (H, W, C) — must match expected inference resolution.
        """
        import numpy as np

        dummy = np.zeros(frame_shape, dtype=np.uint8)
        self.detect(dummy, frame_id=-1)

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(loaded={self._loaded})"

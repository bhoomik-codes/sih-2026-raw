"""
cv.tracking.base
----------------
Abstract base class for multi-object trackers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from cv.detection.base import Detection


class TrackerBase(ABC):
    """
    Abstract interface for object trackers.

    A tracker takes a list of detections (which typically do not have track_ids),
    associates them with existing tracks, and returns a new list of detections
    where track_id is populated.

    Design contract:
    - update() is the only required method.
    - Every Detection in the returned list MUST have track_id set (not None).
    - Detections that cannot be matched to a track are dropped.
    - Calling update([]) is valid — used to tick the tracker's internal clock.
    """

    @abstractmethod
    def update(self, detections: List[Detection]) -> List[Detection]:
        """
        Update the tracker with the latest detections.

        Args:
            detections: List of Detections from the current frame. May be empty.

        Returns:
            List of Detections with track_id populated. May be shorter than
            the input if some detections were filtered by the tracker.
        """
        ...

    def reset(self) -> None:
        """Reset tracker state. Override in subclasses if needed."""
        pass

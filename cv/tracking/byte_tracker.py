"""
cv.tracking.byte_tracker
------------------------
ByteTrack implementation using supervision's core ByteTrack.

Wraps supervision.tracker.byte_tracker.core.ByteTrack directly (avoiding the
deprecated top-level sv.ByteTrack alias) and adds:
  - Per-track trajectory history (last N bottom-center positions)
  - Class-name passthrough
  - Clean conversion to/from our Detection dataclass

Trajectory history is stored in Detection.meta['trajectory'] as a list of
(x, y) tuples (bottom-center pixel coords), oldest first.
"""

from __future__ import annotations

import warnings
from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional, Tuple

import numpy as np

from cv.detection.base import BBox, Detection
from cv.tracking.base import TrackerBase

# Import from the internal module to avoid FutureWarning on sv.ByteTrack
with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    from supervision.tracker.byte_tracker.core import ByteTrack as _SvByteTrack
import supervision as sv


class ByteTracker(TrackerBase):
    """
    ByteTrack-based multi-object tracker.

    Args:
        config: Full YAML config dict. Reads from the ``tracker`` block:
            track_thresh  (float) : Min confidence to enter tracking. Default: 0.25
            track_buffer  (int)   : Frames before a lost track is removed. Default: 30
            match_thresh  (float) : IoU match threshold. Default: 0.8
            min_hits      (int)   : Min consecutive frames to confirm a track. Default: 2
            max_trajectory_len (int): Max positions to store per track. Default: 30
    """

    def __init__(self, config: dict) -> None:
        tracker_cfg = config.get("tracker", {})
        self._track_thresh: float = float(tracker_cfg.get("track_thresh", 0.25))
        self._track_buffer: int = int(tracker_cfg.get("track_buffer", 30))
        self._match_thresh: float = float(tracker_cfg.get("match_thresh", 0.8))
        self._min_hits: int = int(tracker_cfg.get("min_hits", 2))
        self._max_traj_len: int = int(tracker_cfg.get("max_trajectory_len", 30))

        self._tracker = self._build_tracker()

        # Per-track trajectory history: track_id -> deque of (cx, cy) bottom-center
        self._trajectories: Dict[int, Deque[Tuple[float, float]]] = defaultdict(
            lambda: deque(maxlen=self._max_traj_len)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, detections: List[Detection]) -> List[Detection]:
        """
        Update tracker with the latest frame's detections.

        Args:
            detections: Detections from the current inference frame.

        Returns:
            Tracked detections with track_id and meta['trajectory'] populated.
        """
        if not detections:
            # Tick tracker's internal clock even on empty frames
            empty = sv.Detections.empty()
            self._tracker.update_with_detections(empty)
            return []

        # Build a class_id → class_name map from this frame's detections
        cls_name_map: Dict[int, str] = {d.class_id: d.class_name for d in detections}
        frame_id = detections[0].frame_id
        timestamp = detections[0].timestamp

        # Convert to supervision Detections
        sv_dets = sv.Detections(
            xyxy=np.array([d.bbox.as_xyxy() for d in detections], dtype=np.float32),
            confidence=np.array([d.confidence for d in detections], dtype=np.float32),
            class_id=np.array([d.class_id for d in detections], dtype=int),
        )

        # Run ByteTrack update
        tracked = self._tracker.update_with_detections(sv_dets)

        if len(tracked) == 0:
            return []

        results: List[Detection] = []
        for i in range(len(tracked)):
            t_xyxy = tracked.xyxy[i]
            t_conf = float(tracked.confidence[i]) if tracked.confidence is not None else 0.0
            t_cls = int(tracked.class_id[i])
            t_id = int(tracked.tracker_id[i])

            bbox = BBox(
                x1=float(t_xyxy[0]),
                y1=float(t_xyxy[1]),
                x2=float(t_xyxy[2]),
                y2=float(t_xyxy[3]),
            )

            # Update trajectory with bottom-center point
            bc = bbox.bottom_center
            self._trajectories[t_id].append(bc)

            det = Detection(
                bbox=bbox,
                class_id=t_cls,
                class_name=cls_name_map.get(t_cls, f"class_{t_cls}"),
                confidence=t_conf,
                frame_id=frame_id,
                timestamp=timestamp,
                track_id=t_id,
                meta={"trajectory": list(self._trajectories[t_id])},
            )
            results.append(det)

        # Prune trajectories for tracks that no longer appear
        active_ids = {d.track_id for d in results}
        stale = [tid for tid in self._trajectories if tid not in active_ids]
        for tid in stale:
            # Don't delete immediately — the track may return from occlusion
            # We let the deque max-length handle trimming naturally
            pass

        return results

    def reset(self) -> None:
        """Reset tracker and all trajectory histories."""
        self._tracker = self._build_tracker()
        self._trajectories.clear()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_tracker(self) -> _SvByteTrack:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            return _SvByteTrack(
                track_activation_threshold=self._track_thresh,
                lost_track_buffer=self._track_buffer,
                minimum_matching_threshold=self._match_thresh,
                minimum_consecutive_frames=self._min_hits,
            )

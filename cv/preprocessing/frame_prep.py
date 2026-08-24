"""
cv.preprocessing.frame_prep
-----------------------------
Frame preprocessing utilities for the IBVAP edge pipeline.

Design notes:
- All functions are pure: they accept and return numpy arrays.
- No GPU operations here — preprocessing is intentionally CPU-side to
  keep the YOLO model's CUDA stream free for inference.
- ROI masking happens before resizing, so the detector only sees the
  region of interest.
- YOLO performs its own normalization internally (divides by 255,
  applies letterbox padding). Do NOT manually normalize before passing
  to YOLODetector — it will double-normalize.
"""

from __future__ import annotations

import logging
from typing import Optional, Sequence, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def resize_frame(
    frame: np.ndarray,
    target_wh: Tuple[int, int],
    interpolation: int = cv2.INTER_LINEAR,
) -> np.ndarray:
    """
    Resize a BGR frame to the target (width, height).

    Args:
        frame:         BGR numpy array (H, W, 3).
        target_wh:     (width, height) target resolution.
        interpolation: OpenCV interpolation flag. INTER_LINEAR is fast and
                       suitable for downscaling to inference resolution.

    Returns:
        Resized BGR frame. Returns original frame if dimensions already match.
    """
    target_w, target_h = target_wh
    h, w = frame.shape[:2]

    if w == target_w and h == target_h:
        return frame

    resized = cv2.resize(frame, (target_w, target_h), interpolation=interpolation)
    return resized


def normalize_frame(frame: np.ndarray) -> np.ndarray:
    """
    Normalize a BGR frame to float32 [0.0, 1.0].

    WARNING: Do NOT call this before passing to YOLODetector.
    Ultralytics YOLO normalizes internally. This function is provided
    for potential future use with custom ONNX/TensorRT pipelines that
    require pre-normalized input.

    Args:
        frame: BGR uint8 numpy array (H, W, 3).

    Returns:
        float32 numpy array in range [0.0, 1.0].
    """
    return (frame.astype(np.float32) / 255.0)


def apply_roi(
    frame: np.ndarray,
    roi_polygon: Optional[Sequence[Tuple[int, int]]],
) -> np.ndarray:
    """
    Mask a frame to a region of interest (ROI) polygon.

    Pixels outside the polygon are set to black (0). The returned frame
    has the same shape as the input — the ROI is NOT cropped, so
    bounding box coordinates remain in the original frame coordinate space.

    If roi_polygon is None or empty, the original frame is returned unchanged.

    Args:
        frame:       BGR numpy array (H, W, 3).
        roi_polygon: List of (x, y) pixel coordinate tuples defining the ROI
                     boundary. The polygon is automatically closed.

                     Example (full-frame, effectively no-op):
                         [(0, 0), (W, 0), (W, H), (0, H)]

                     Example (lower half only):
                         [(0, H//2), (W, H//2), (W, H), (0, H)]

    Returns:
        BGR frame with pixels outside the ROI set to zero.
    """
    if not roi_polygon:
        return frame

    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    pts = np.array(roi_polygon, dtype=np.int32).reshape((-1, 1, 2))
    cv2.fillPoly(mask, [pts], color=255)

    masked = cv2.bitwise_and(frame, frame, mask=mask)
    return masked


def build_preprocessing_pipeline(config: dict):
    """
    Factory: builds a callable that applies all configured preprocessing
    steps to a frame in the correct order.

    Config keys (from the YAML `preprocessing` block):
        resize     (list[int] | null): [width, height]. Null = no resize.
        roi_polygon (list[list] | null): Polygon as list of [x, y] pairs.

    Returns:
        Callable[[np.ndarray], np.ndarray] — the preprocessing function.

    Usage:
        preprocess = build_preprocessing_pipeline(config["preprocessing"])
        processed = preprocess(raw_frame)
    """
    prep_cfg = config.get("preprocessing", {})

    resize_target: Optional[Tuple[int, int]] = None
    raw_resize = prep_cfg.get("resize", None)
    if raw_resize and len(raw_resize) == 2:
        resize_target = (int(raw_resize[0]), int(raw_resize[1]))

    roi_polygon = None
    raw_roi = prep_cfg.get("roi_polygon", None)
    if raw_roi:
        roi_polygon = [tuple(pt) for pt in raw_roi]

    def preprocess(frame: np.ndarray) -> np.ndarray:
        # Step 1: Apply ROI masking before resize so that the detector
        # input only contains the operator-defined zone.
        if roi_polygon:
            frame = apply_roi(frame, roi_polygon)

        # Step 2: Resize to inference resolution.
        if resize_target:
            frame = resize_frame(frame, resize_target)

        return frame

    logger.info(
        "Preprocessing pipeline built  resize=%s  roi=%s",
        resize_target,
        "yes" if roi_polygon else "no",
    )
    return preprocess

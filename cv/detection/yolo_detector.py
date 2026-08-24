"""
cv.detection.yolo_detector
---------------------------
YOLOv8/v11 detector implementation using Ultralytics.

Wraps Ultralytics YOLO and returns normalized Detection objects.
The rest of the system never imports anything from Ultralytics directly.

Usage:
    detector = YOLODetector(config)
    detector.load()
    detector.warmup()
    detections = detector.detect(frame, frame_id=42)
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np

from cv.detection.base import BBox, Detection, DetectorBase

logger = logging.getLogger(__name__)

# COCO class IDs that are relevant to border surveillance.
# We ignore all other detected classes to reduce noise.
_RELEVANT_CLASS_IDS: set[int] = {
    0,  # person
    2,  # car
    3,  # motorcycle
    5,  # bus
    7,  # truck
}

# Human-readable names for the relevant COCO classes
_CLASS_NAMES: dict[int, str] = {
    0: "person",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


class YOLODetector(DetectorBase):
    """
    YOLO-based object detector (PyTorch backend via Ultralytics).

    Config keys (all from the YAML `detector` block):
        model_path       (str)   : Path to .pt weights file. Default: "yolov8n.pt"
        device           (str)   : "cuda:0", "cpu". Default: "cuda:0"
        conf_threshold   (float) : Minimum confidence to report. Default: 0.40
        iou_threshold    (float) : NMS IoU threshold. Default: 0.45
        imgsz            (int)   : Inference resolution (square). Default: 640
        half             (bool)  : Use FP16 inference. Default: False (Phase 7)
        classes          (list)  : Override default relevant class IDs.
        verbose          (bool)  : Suppress Ultralytics console spam. Default: False

    Phase 7 note:
        Set half=True once TensorRT/ONNX pipelines are validated. In Phase 1,
        keep FP32 for a clean baseline.
    """

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._model = None

        # Resolve config with sensible defaults
        det_cfg = config.get("detector", config)  # accept both flat & nested dicts
        self._model_path: str = det_cfg.get("model", "yolov8n.pt")
        self._device: str = det_cfg.get("device", "cuda:0")
        self._conf: float = float(det_cfg.get("conf_threshold", 0.40))
        self._iou: float = float(det_cfg.get("iou_threshold", 0.45))
        self._imgsz: int = int(det_cfg.get("imgsz", 640))
        self._half: bool = bool(det_cfg.get("half", False))
        self._verbose: bool = bool(det_cfg.get("verbose", False))

        # Class filter — override via config if needed
        raw_classes = det_cfg.get("classes", None)
        self._relevant_ids: set[int] = (
            set(map(int, raw_classes)) if raw_classes else _RELEVANT_CLASS_IDS
        )

    def load(self) -> None:
        """
        Load YOLO weights from disk onto the target device.

        Raises:
            RuntimeError: If CUDA is requested but unavailable.
            FileNotFoundError: If model_path points to a missing local file.
        """
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "Ultralytics is not installed. Run: pip install ultralytics"
            ) from exc

        logger.info("Loading YOLO model: %s → device=%s", self._model_path, self._device)
        self._model = YOLO(self._model_path, verbose=self._verbose)
        self._model.to(self._device)

        if self._half:
            logger.info("FP16 (half) mode enabled — Phase 7+ only")

        self._loaded = True
        logger.info(
            "YOLODetector ready  model=%s  conf=%.2f  iou=%.2f  imgsz=%d  device=%s",
            self._model_path,
            self._conf,
            self._iou,
            self._imgsz,
            self._device,
        )

    def detect(self, frame: np.ndarray, frame_id: int = 0) -> List[Detection]:
        """
        Run YOLO inference on a single BGR frame.

        Args:
            frame:    BGR numpy array (H, W, 3). Must not be None or empty.
            frame_id: Caller-assigned sequential frame number.

        Returns:
            List[Detection] — only objects in _relevant_ids, above conf_threshold.
        """
        if not self._loaded:
            raise RuntimeError("Call detector.load() before detect().")

        if frame is None or frame.size == 0:
            logger.warning("detect() received an empty frame (frame_id=%d)", frame_id)
            return []

        try:
            results = self._model.predict(
                source=frame,
                conf=self._conf,
                iou=self._iou,
                imgsz=self._imgsz,
                half=self._half,
                device=self._device,
                verbose=False,  # always suppress per-frame console spam
                stream=False,
            )
        except Exception as exc:
            logger.error("YOLO inference failed on frame %d: %s", frame_id, exc)
            return []

        detections: List[Detection] = []

        # Ultralytics returns one Results object per image (we always send one)
        result = results[0]
        if result.boxes is None:
            return []

        import time

        ts = time.time()

        for box in result.boxes:
            class_id = int(box.cls.item())

            # Filter irrelevant classes early
            if class_id not in self._relevant_ids:
                continue

            conf = float(box.conf.item())
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            detections.append(
                Detection(
                    bbox=BBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    class_id=class_id,
                    class_name=_CLASS_NAMES.get(class_id, f"class_{class_id}"),
                    confidence=conf,
                    frame_id=frame_id,
                    timestamp=ts,
                )
            )

        return detections

"""
cv.detection.onnx_detector
----------------------------
ONNX Runtime detector implementation (Phase 7).

Runs YOLOv8 (or any compatible object detection model) via ONNX Runtime,
using the CUDA execution provider for GPU-accelerated inference.

This is a drop-in replacement for YOLODetector. The rest of the system never
imports anything from onnxruntime or ultralytics directly.

Export a model first:
    python scripts/export_onnx.py

Then use via config:
    detector:
      backend: onnx
      model: "models/onnx/yolov8n.onnx"
      device: "cuda:0"
      conf_threshold: 0.25
      iou_threshold: 0.45
      imgsz: 640

Note on normalization:
    Unlike the Ultralytics Python API, raw ONNX inference requires manual
    preprocessing: letterbox resize + normalize to [0, 1] + CHW transpose.
    We use Ultralytics' own letterbox util for consistency.
"""

from __future__ import annotations

import logging
import time
from typing import List

import cv2
import numpy as np

from cv.detection.base import BBox, Detection, DetectorBase

logger = logging.getLogger(__name__)

# COCO class IDs relevant to border surveillance
_RELEVANT_CLASS_IDS: set[int] = {0, 2, 3, 5, 7}
_CLASS_NAMES: dict[int, str] = {
    0: "person",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


class ONNXDetector(DetectorBase):
    """
    ONNX Runtime-based object detector (Phase 7 — PyTorch → ONNX optimization).

    Config keys (all from the YAML `detector` block):
        model_path       (str)   : Path to .onnx model file.
        device           (str)   : "cuda:0" or "cpu". Default: "cuda:0".
        conf_threshold   (float) : Minimum confidence. Default: 0.25.
        iou_threshold    (float) : NMS IoU threshold. Default: 0.45.
        imgsz            (int)   : Input resolution (square). Default: 640.
        classes          (list)  : Override default relevant class IDs.
    """

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._session = None

        det_cfg = config.get("detector", config)
        self._model_path: str = det_cfg.get("model", "models/onnx/yolov8n.onnx")
        self._device: str = det_cfg.get("device", "cuda:0")
        self._conf: float = float(det_cfg.get("conf_threshold", 0.25))
        self._iou: float = float(det_cfg.get("iou_threshold", 0.45))
        self._imgsz: int = int(det_cfg.get("imgsz", 640))

        raw_classes = det_cfg.get("classes", None)
        self._relevant_ids: set[int] = (
            set(map(int, raw_classes)) if raw_classes else _RELEVANT_CLASS_IDS
        )

        # Input name / output name — discovered after load()
        self._input_name: str = "images"
        self._output_name: str = "output0"

    # ------------------------------------------------------------------
    # DetectorBase interface
    # ------------------------------------------------------------------

    def load(self) -> None:
        """
        Load the ONNX model and create an inference session.

        Raises:
            RuntimeError: If onnxruntime is not installed.
            FileNotFoundError: If model_path does not exist.
        """
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError(
                "onnxruntime is not installed. Run: pip install onnxruntime-gpu"
            ) from exc

        # Choose execution provider based on device
        if "cuda" in self._device.lower():
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]

        logger.info(
            "Loading ONNX model: %s → providers=%s",
            self._model_path,
            providers,
        )
        self._session = ort.InferenceSession(self._model_path, providers=providers)

        # Discover actual input/output names from the model
        self._input_name = self._session.get_inputs()[0].name
        self._output_name = self._session.get_outputs()[0].name

        self._loaded = True
        logger.info(
            "ONNXDetector ready  model=%s  conf=%.2f  iou=%.2f  imgsz=%d",
            self._model_path,
            self._conf,
            self._iou,
            self._imgsz,
        )

    def detect(self, frame: np.ndarray, frame_id: int = 0) -> List[Detection]:
        """
        Run ONNX inference on a single BGR frame.

        Args:
            frame:    BGR numpy array (H, W, 3).
            frame_id: Caller-assigned sequential frame number.

        Returns:
            List[Detection] — filtered and NMS-applied detections.
        """
        if not self._loaded:
            raise RuntimeError("Call detector.load() before detect().")

        if frame is None or frame.size == 0:
            logger.warning("detect() received an empty frame (frame_id=%d)", frame_id)
            return []

        orig_h, orig_w = frame.shape[:2]

        # --- Preprocess ---
        blob, scale, (pad_x, pad_y) = self._letterbox(frame, self._imgsz)
        # HWC BGR → CHW RGB → float32 / 255
        blob = blob[:, :, ::-1].transpose(2, 0, 1)          # BGR→RGB, HWC→CHW
        blob = np.ascontiguousarray(blob, dtype=np.float32) / 255.0
        blob = blob[np.newaxis, ...]                          # add batch dim

        # --- Inference ---
        try:
            outputs = self._session.run(
                [self._output_name],
                {self._input_name: blob},
            )
        except Exception as exc:
            logger.error("ONNX inference failed on frame %d: %s", frame_id, exc)
            return []

        # --- Postprocess ---
        # YOLOv8 ONNX output shape: (1, 84, N) — [cx, cy, w, h, cls0..cls79]
        preds = outputs[0][0].T    # (N, 84)
        return self._postprocess(preds, orig_w, orig_h, scale, pad_x, pad_y, frame_id)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _letterbox(
        img: np.ndarray,
        new_size: int,
        color: tuple = (114, 114, 114),
    ):
        """Letterbox resize maintaining aspect ratio. Returns (resized, scale, (pad_x, pad_y))."""
        h, w = img.shape[:2]
        scale = min(new_size / h, new_size / w)
        new_h, new_w = int(round(h * scale)), int(round(w * scale))
        pad_x = (new_size - new_w) / 2
        pad_y = (new_size - new_h) / 2
        top, bottom = int(round(pad_y - 0.1)), int(round(pad_y + 0.1))
        left, right = int(round(pad_x - 0.1)), int(round(pad_x + 0.1))
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        padded = cv2.copyMakeBorder(
            resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
        )
        return padded, scale, (pad_x, pad_y)

    def _postprocess(
        self,
        preds: np.ndarray,
        orig_w: int,
        orig_h: int,
        scale: float,
        pad_x: float,
        pad_y: float,
        frame_id: int,
    ) -> List[Detection]:
        """
        Decode raw YOLOv8 ONNX predictions into Detection objects.

        Args:
            preds:   (N, 84) array: first 4 cols are [cx, cy, w, h],
                     next 80 are class scores.
            orig_w, orig_h: Original frame dimensions (before letterbox).
            scale:   Letterbox scale factor.
            pad_x, pad_y: Letterbox padding in pixels.
            frame_id: Passed through to Detection.

        Returns:
            List[Detection] after NMS.
        """
        if preds.shape[0] == 0:
            return []

        # Scores for each class
        class_scores = preds[:, 4:]      # (N, 80)
        class_ids = np.argmax(class_scores, axis=1)   # (N,)
        confidences = class_scores[np.arange(len(class_scores)), class_ids]

        # Filter by relevance and confidence
        mask = (
            np.isin(class_ids, list(self._relevant_ids)) &
            (confidences >= self._conf)
        )
        preds = preds[mask]
        class_ids = class_ids[mask]
        confidences = confidences[mask]

        if len(preds) == 0:
            return []

        # cx, cy, w, h → x1, y1, x2, y2 in letterboxed coords
        cx, cy, bw, bh = preds[:, 0], preds[:, 1], preds[:, 2], preds[:, 3]
        x1 = cx - bw / 2
        y1 = cy - bh / 2
        x2 = cx + bw / 2
        y2 = cy + bh / 2

        # Remove letterbox padding and scale back to original coords
        x1 = (x1 - pad_x) / scale
        y1 = (y1 - pad_y) / scale
        x2 = (x2 - pad_x) / scale
        y2 = (y2 - pad_y) / scale

        # Clamp to frame bounds
        x1 = np.clip(x1, 0, orig_w)
        y1 = np.clip(y1, 0, orig_h)
        x2 = np.clip(x2, 0, orig_w)
        y2 = np.clip(y2, 0, orig_h)

        # Apply NMS
        boxes_xywh = np.stack([x1, y1, x2 - x1, y2 - y1], axis=1).tolist()
        confidences_list = confidences.tolist()
        indices = cv2.dnn.NMSBoxes(
            boxes_xywh, confidences_list, self._conf, self._iou
        )
        if len(indices) == 0:
            return []

        ts = time.time()
        detections: List[Detection] = []
        for idx in np.array(indices).flatten():
            cid = int(class_ids[idx])
            detections.append(
                Detection(
                    bbox=BBox(
                        x1=float(x1[idx]),
                        y1=float(y1[idx]),
                        x2=float(x2[idx]),
                        y2=float(y2[idx]),
                    ),
                    class_id=cid,
                    class_name=_CLASS_NAMES.get(cid, f"class_{cid}"),
                    confidence=float(confidences[idx]),
                    frame_id=frame_id,
                    timestamp=ts,
                )
            )

        return detections

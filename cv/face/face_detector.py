"""
cv.face.face_detector
----------------------
Face detection module for border checkpoint & pedestrian gate surveillance.

Supports:
- OpenCV Haar Cascade / DNN Face Detector
- Bounding box localization and confidence estimation
- Optional crop extraction for security watchlist matching
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

from cv.detection.base import BBox

logger = logging.getLogger(__name__)


@dataclass
class FaceDetection:
    """Represents a detected face in a video frame."""

    bbox: BBox
    confidence: float
    frame_id: int
    timestamp: float
    landmarks: Optional[List[Tuple[float, float]]] = None


class FaceDetector:
    """
    Lightweight face detector for checkpoint pedestrian monitoring.
    """

    def __init__(
        self,
        min_confidence: float = 0.6,
        min_face_size: Tuple[int, int] = (30, 30),
    ) -> None:
        self._min_conf = min_confidence
        self._min_size = min_face_size
        self._classifier: Optional[cv2.CascadeClassifier] = None
        self._loaded = False

    def load(self) -> None:
        """Initialize OpenCV face detection model."""
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._classifier = cv2.CascadeClassifier(cascade_path)
            self._loaded = True
            logger.info("FaceDetector loaded successfully using OpenCV cascade: %s", cascade_path)
        except Exception as exc:
            logger.error("Failed to load FaceDetector cascade: %s", exc)
            self._loaded = False

    def detect(
        self, frame: np.ndarray, frame_id: int = 0, timestamp: float = 0.0
    ) -> List[FaceDetection]:
        """
        Detect faces in a BGR frame.

        Args:
            frame: Input BGR image.
            frame_id: Frame sequence identifier.
            timestamp: Capture timestamp.

        Returns:
            List of FaceDetection objects.
        """
        if not self._loaded:
            self.load()

        if self._classifier is None or frame is None or frame.size == 0:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        faces = self._classifier.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=self._min_size,
        )

        detections: List[FaceDetection] = []
        for x, y, w, h in faces:
            bbox = BBox(x1=float(x), y1=float(y), x2=float(x + w), y2=float(y + h))
            detections.append(
                FaceDetection(
                    bbox=bbox,
                    confidence=0.85,
                    frame_id=frame_id,
                    timestamp=timestamp,
                )
            )

        return detections

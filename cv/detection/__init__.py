"""
cv.detection — Detector abstraction layer.

All downstream code (tracker, event engine) interacts only with
the DetectorBase interface and the Detection dataclass.
No model-specific types leak beyond this package.
"""

from cv.detection.base import Detection, DetectorBase
from cv.detection.yolo_detector import YOLODetector

__all__ = ["Detection", "DetectorBase", "YOLODetector"]

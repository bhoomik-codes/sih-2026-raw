"""
cv.face
-------
Face detection and recognition module for border surveillance.
"""

from cv.face.face_detector import FaceDetection, FaceDetector
from cv.face.recognition_engine import FaceIdentity, FaceRecognitionEngine, UNKNOWN_IDENTITY

__all__ = [
    "FaceDetection",
    "FaceDetector",
    "FaceIdentity",
    "FaceRecognitionEngine",
    "UNKNOWN_IDENTITY",
]

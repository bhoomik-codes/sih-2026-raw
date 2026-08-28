"""
cv.anpr
-------
License plate detection, preprocessing, and OCR module.
"""

from cv.anpr.plate_pipeline import (
    PlateOCR,
    PlateOCRResult,
    PlatePreprocessor,
)

__all__ = [
    "PlateOCR",
    "PlateOCRResult",
    "PlatePreprocessor",
]

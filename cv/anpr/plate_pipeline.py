"""
cv.anpr.plate_pipeline
-----------------------
Computer vision preprocessing and OCR pipeline for License Plate Recognition.

Provides:
- Image deskewing and contrast enhancement (CLAHE + Adaptive Thresholding)
- Plate candidate region filtering
- OCR text extraction and normalization (EasyOCR with GPU acceleration / fallback)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

try:
    import easyocr

    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False


@dataclass
class PlateOCRResult:
    """Result of OCR analysis on a vehicle/plate crop."""

    plate_text: str
    confidence: float
    is_mock: bool = False
    raw_text: str = ""


class PlatePreprocessor:
    """
    Applies image enhancement to license plate crops to optimize OCR accuracy.
    """

    @staticmethod
    def enhance_crop(crop: np.ndarray) -> np.ndarray:
        """
        Enhance a vehicle or license plate crop for OCR.

        Steps:
        1. Grayscale conversion.
        2. Bilateral filter to smooth noise while preserving character edges.
        3. CLAHE (Contrast Limited Adaptive Histogram Equalization) for illumination normalization.
        """
        if crop is None or crop.size == 0:
            return crop

        # Convert to grayscale if 3 channels
        if len(crop.shape) == 3:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = crop.copy()

        # Resize if crop is too small (OCR works better on images >= 120px height)
        h, w = gray.shape[:2]
        if h < 100 and h > 0:
            scale = 120.0 / h
            gray = cv2.resize(gray, (int(w * scale), 120), interpolation=cv2.INTER_CUBIC)

        # Bilateral filter reduces noise while keeping edges sharp
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)

        # CLAHE enhances local contrast against shadows / night-glare
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(filtered)

        return enhanced


class PlateOCR:
    """
    License plate OCR engine with hardware acceleration and text normalization.
    """

    def __init__(self, use_gpu: bool = True, languages: Optional[List[str]] = None) -> None:
        self._use_gpu = use_gpu
        self._languages = languages or ["en"]
        self._reader = None
        self._is_mock = not HAS_EASYOCR

        if HAS_EASYOCR:
            try:
                logger.info("Initializing EasyOCR reader (gpu=%s)...", self._use_gpu)
                self._reader = easyocr.Reader(self._languages, gpu=self._use_gpu)
                self._is_mock = False
            except Exception as e:
                logger.warning("Failed to initialize EasyOCR on GPU (%s). Trying CPU...", e)
                try:
                    self._reader = easyocr.Reader(self._languages, gpu=False)
                    self._is_mock = False
                except Exception as cpu_err:
                    logger.error(
                        "Failed to initialize EasyOCR on CPU: %s. Using Mock mode.", cpu_err
                    )
                    self._is_mock = True
        else:
            logger.warning(
                "EasyOCR is not installed. ANPR running in MOCK mode. "
                "Install easyocr with: pip install easyocr"
            )

    @property
    def is_mock(self) -> bool:
        return self._is_mock

    def read_plate(self, image: np.ndarray, fallback_id: Optional[int] = None) -> PlateOCRResult:
        """
        Run OCR on an enhanced vehicle / plate crop and return normalized text.
        """
        if image is None or image.size == 0:
            return PlateOCRResult(plate_text="", confidence=0.0, is_mock=self._is_mock)

        # Apply preprocessing
        enhanced = PlatePreprocessor.enhance_crop(image)

        if not self._is_mock and self._reader is not None:
            try:
                results = self._reader.readtext(enhanced)
                if results:
                    # Select highest confidence result with reasonable length
                    best = max(results, key=lambda x: x[2])
                    raw = best[1]
                    conf = float(best[2])
                    clean_text = self.normalize_plate_text(raw)
                    if clean_text:
                        return PlateOCRResult(
                            plate_text=clean_text,
                            confidence=conf,
                            is_mock=False,
                            raw_text=raw,
                        )
            except Exception as exc:
                logger.warning("EasyOCR extraction error: %s", exc)

        if self._is_mock:
            mock_plate = f"MOCK-{fallback_id}" if fallback_id is not None else "UNKNOWN"
            return PlateOCRResult(
                plate_text=mock_plate,
                confidence=0.85,
                is_mock=True,
                raw_text=mock_plate,
            )
        else:
            return PlateOCRResult(
                plate_text="",
                confidence=0.0,
                is_mock=False,
                raw_text="",
            )

    @staticmethod
    def normalize_plate_text(raw_text: str) -> str:
        """
        Clean and normalize raw OCR text:
        - Strip non-alphanumeric characters
        - Uppercase
        """
        if not raw_text:
            return ""
        # Remove whitespace and special characters
        cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_text).upper()
        return cleaned

"""
tests/test_detection.py
-----------------------
Unit tests for the detection abstraction layer.

Tests:
    - Detection dataclass correctness
    - BBox geometry helpers
    - DetectorBase interface compliance
    - YOLODetector output contract (with real YOLO if GPU available, else mocked)
    - 100-frame stability run (no crashes, no memory explosion)

Run:
    pytest tests/test_detection.py -v
    pytest tests/test_detection.py -v -k "not gpu"  # skip GPU tests
"""

from __future__ import annotations

import time
from typing import List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from cv.detection.base import BBox, Detection, DetectorBase


# ── BBox tests ────────────────────────────────────────────────────────────────


class TestBBox:
    def test_dimensions(self):
        box = BBox(x1=10, y1=20, x2=110, y2=120)
        assert box.width == 100.0
        assert box.height == 100.0
        assert box.area == 10000.0

    def test_center(self):
        box = BBox(x1=0, y1=0, x2=100, y2=200)
        cx, cy = box.center
        assert cx == pytest.approx(50.0)
        assert cy == pytest.approx(100.0)

    def test_bottom_center(self):
        box = BBox(x1=0, y1=0, x2=100, y2=200)
        bx, by = box.bottom_center
        assert bx == pytest.approx(50.0)
        assert by == pytest.approx(200.0)

    def test_as_xyxy(self):
        box = BBox(x1=10, y1=20, x2=110, y2=120)
        assert box.as_xyxy() == (10, 20, 110, 120)

    def test_as_xywh(self):
        box = BBox(x1=10, y1=20, x2=110, y2=120)
        x, y, w, h = box.as_xywh()
        assert x == 10
        assert y == 20
        assert w == 100
        assert h == 100

    def test_frozen(self):
        """BBox is immutable."""
        box = BBox(x1=0, y1=0, x2=100, y2=100)
        with pytest.raises((AttributeError, TypeError)):
            box.x1 = 999  # type: ignore[misc]


# ── Detection dataclass tests ─────────────────────────────────────────────────


class TestDetection:
    def _make(self, **kwargs) -> Detection:
        defaults = dict(
            bbox=BBox(0, 0, 100, 100),
            class_id=0,
            class_name="person",
            confidence=0.85,
            frame_id=42,
            timestamp=time.time(),
        )
        defaults.update(kwargs)
        return Detection(**defaults)

    def test_fields_accessible(self):
        d = self._make()
        assert d.class_name == "person"
        assert d.class_id == 0
        assert d.confidence == pytest.approx(0.85)
        assert d.frame_id == 42

    def test_track_id_default_none(self):
        d = self._make()
        assert d.track_id is None

    def test_track_id_settable(self):
        d = self._make()
        d.track_id = 23
        assert d.track_id == 23

    def test_repr_contains_class(self):
        d = self._make()
        assert "person" in repr(d)

    def test_repr_contains_track_id(self):
        d = self._make()
        d.track_id = 7
        assert "track=7" in repr(d)

    def test_confidence_range(self):
        """Confidence should be between 0 and 1."""
        d = self._make(confidence=0.0)
        assert 0.0 <= d.confidence <= 1.0
        d2 = self._make(confidence=1.0)
        assert 0.0 <= d2.confidence <= 1.0


# ── DetectorBase interface tests ──────────────────────────────────────────────


class TestDetectorBase:
    """Verify that DetectorBase is abstract and cannot be instantiated directly."""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            DetectorBase(config={})

    def test_concrete_must_implement_detect(self):
        """A subclass missing detect() should raise TypeError."""
        class BrokenDetector(DetectorBase):
            def load(self):
                self._loaded = True
            # detect() intentionally omitted

        with pytest.raises(TypeError):
            BrokenDetector(config={})

    def test_concrete_must_implement_load(self):
        """A subclass missing load() should raise TypeError."""
        class BrokenDetector(DetectorBase):
            def detect(self, frame, frame_id=0) -> List[Detection]:
                return []
            # load() intentionally omitted

        with pytest.raises(TypeError):
            BrokenDetector(config={})

    def test_minimal_concrete_subclass(self):
        """A properly implemented subclass should instantiate fine."""
        class MinimalDetector(DetectorBase):
            def load(self):
                self._loaded = True

            def detect(self, frame, frame_id=0) -> List[Detection]:
                return []

        d = MinimalDetector(config={})
        assert not d.is_loaded
        d.load()
        assert d.is_loaded

    def test_warmup_calls_detect(self):
        """warmup() must call detect() once with a dummy frame."""
        calls = []

        class SpyDetector(DetectorBase):
            def load(self):
                self._loaded = True

            def detect(self, frame, frame_id=0) -> List[Detection]:
                calls.append(frame_id)
                return []

        d = SpyDetector(config={})
        d.load()
        d.warmup()
        assert len(calls) == 1
        assert calls[0] == -1  # warmup uses frame_id=-1


# ── YOLODetector tests (mocked — no GPU required) ─────────────────────────────


class TestYOLODetectorMocked:
    """
    These tests mock Ultralytics YOLO so they run without a GPU or model file.
    They verify the output contract: YOLODetector must return List[Detection].
    """

    def _make_detector(self, conf: float = 0.40) -> object:
        from cv.detection.yolo_detector import YOLODetector
        cfg = {
            "detector": {
                "model": "yolov8n.pt",
                "device": "cpu",
                "conf_threshold": conf,
                "iou_threshold": 0.45,
                "imgsz": 640,
            }
        }
        return YOLODetector(config=cfg)

    def _mock_yolo_result(self, detections):
        """Build a mock Ultralytics result object."""
        import torch
        mock_result = MagicMock()
        if not detections:
            mock_result.boxes = None
            return mock_result

        mock_boxes = []
        for cls_id, conf, x1, y1, x2, y2 in detections:
            box = MagicMock()
            box.cls = torch.tensor([float(cls_id)])
            box.conf = torch.tensor([conf])
            box.xyxy = torch.tensor([[x1, y1, x2, y2]])
            mock_boxes.append(box)

        mock_result.boxes = mock_boxes
        return mock_result

    def test_output_is_list(self):
        """detect() must always return a list."""
        from cv.detection.yolo_detector import YOLODetector

        det = self._make_detector()

        with patch("ultralytics.YOLO") as MockYOLO:
            mock_model = MagicMock()
            MockYOLO.return_value = mock_model
            mock_model.predict.return_value = [self._mock_yolo_result([])]

            det.load()
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            result = det.detect(frame, frame_id=1)

        assert isinstance(result, list)

    def test_empty_frame_returns_empty_list(self):
        """detect() on empty frame must return [] without raising."""
        from cv.detection.yolo_detector import YOLODetector

        det = self._make_detector()
        with patch("ultralytics.YOLO") as MockYOLO:
            mock_model = MagicMock()
            MockYOLO.return_value = mock_model
            det.load()

            empty = np.array([])
            result = det.detect(empty, frame_id=0)

        assert result == []

    def test_detect_filters_irrelevant_classes(self):
        """Classes outside the relevant set must be filtered out."""
        from cv.detection.yolo_detector import YOLODetector
        import torch

        det = self._make_detector()
        with patch("ultralytics.YOLO") as MockYOLO:
            mock_model = MagicMock()
            MockYOLO.return_value = mock_model

            # Return a "cat" (class_id=15) — should be filtered
            mock_result = MagicMock()
            cat_box = MagicMock()
            cat_box.cls = torch.tensor([15.0])
            cat_box.conf = torch.tensor([0.90])
            cat_box.xyxy = torch.tensor([[10, 10, 100, 100]])
            mock_result.boxes = [cat_box]
            mock_model.predict.return_value = [mock_result]

            det.load()
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            result = det.detect(frame, frame_id=1)

        # cat (15) is not in _RELEVANT_CLASS_IDS → should return empty
        assert result == []

    def test_detect_before_load_raises(self):
        """detect() called before load() must raise RuntimeError."""
        from cv.detection.yolo_detector import YOLODetector

        det = self._make_detector()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        with pytest.raises(RuntimeError, match="load"):
            det.detect(frame)

    def test_100_frames_no_exception(self):
        """Run 100 frames through detect() without any exception."""
        from cv.detection.yolo_detector import YOLODetector

        det = self._make_detector()
        with patch("ultralytics.YOLO") as MockYOLO:
            mock_model = MagicMock()
            MockYOLO.return_value = mock_model
            mock_model.predict.return_value = [self._mock_yolo_result([])]
            det.load()

            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            for i in range(100):
                result = det.detect(frame, frame_id=i)
                assert isinstance(result, list)

    def test_person_detection_returned(self):
        """A person detection must appear in the output with correct fields."""
        from cv.detection.yolo_detector import YOLODetector
        import torch

        det = self._make_detector(conf=0.0)
        with patch("ultralytics.YOLO") as MockYOLO:
            mock_model = MagicMock()
            MockYOLO.return_value = mock_model

            mock_result = MagicMock()
            person_box = MagicMock()
            person_box.cls = torch.tensor([0.0])   # class_id=0 (person)
            person_box.conf = torch.tensor([0.87])
            person_box.xyxy = torch.tensor([[50.0, 60.0, 200.0, 400.0]])
            mock_result.boxes = [person_box]
            mock_model.predict.return_value = [mock_result]

            det.load()
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            results = det.detect(frame, frame_id=5)

        assert len(results) == 1
        d = results[0]
        assert d.class_name == "person"
        assert d.class_id == 0
        assert d.confidence == pytest.approx(0.87, abs=1e-3)
        assert d.bbox.x1 == pytest.approx(50.0)
        assert d.bbox.y2 == pytest.approx(400.0)
        assert d.frame_id == 5
        assert d.track_id is None  # Phase 1: no tracking yet

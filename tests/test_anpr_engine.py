"""
tests.test_anpr_engine
----------------------
Tests for the ANPREngine.
"""

import time
import numpy as np
from cv.detection.base import BBox, Detection
from intelligence.anpr.engine import ANPREngine
from intelligence.events.base import EventType, EventSeverity

class MockReader:
    def readtext(self, img):
        return [([0,0,0,0], "MH12AB1234", 0.99)]

def test_anpr_engine_buffering_and_early_read():
    cfg = {
        "anpr_engine": {
            "enabled": True,
            "min_crop_area": 100,
            "watchlist": ["MH12AB1234"]
        }
    }
    engine = ANPREngine(cfg, camera_name="TEST")
    # Mock the reader
    engine._reader = MockReader()

    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    events = []
    # Send 14 frames - should buffer, no read
    for i in range(14):
        det = Detection(
            bbox=BBox(10, 10, 50, 50),
            class_id=2, class_name="car", confidence=0.9, frame_id=i, timestamp=time.time(), track_id=1
        )
        events.extend(engine.update(frame, [det]))
        
    assert len(events) == 0
    assert len(engine._buffers[1].crops) == 14
    assert not engine._buffers[1].ocr_run
    
    # 15th frame - should trigger early read
    det = Detection(
        bbox=BBox(10, 10, 50, 50),
        class_id=2, class_name="car", confidence=0.9, frame_id=14, timestamp=time.time(), track_id=1
    )
    events.extend(engine.update(frame, [det]))
    
    assert len(events) == 1
    assert events[0].event_type == EventType.VEHICLE_ANPR
    assert events[0].severity == EventSeverity.CRITICAL
    assert events[0].details["plate"] == "MH12AB1234"
    assert engine._buffers[1].ocr_run

def test_anpr_engine_stale_track_cleanup():
    cfg = {
        "anpr_engine": {
            "enabled": True,
            "min_crop_area": 100,
            "watchlist": ["MH12AB1234"]
        }
    }
    engine = ANPREngine(cfg, camera_name="TEST")
    engine._reader = MockReader()
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    det = Detection(
        bbox=BBox(10, 10, 50, 50),
        class_id=2, class_name="car", confidence=0.9, frame_id=1, timestamp=time.time() - 3.0, track_id=2
    )
    engine._buffers[2] = __import__("intelligence.anpr.engine").anpr.engine._VehicleTrackBuffer(2)
    engine._buffers[2].add_crop(frame, det)
    
    # Update with empty detections -> track 2 is stale and > 2s old
    events = engine.update(frame, [])
    
    assert len(events) == 1
    assert events[0].event_type == EventType.VEHICLE_ANPR
    assert 2 not in engine._buffers

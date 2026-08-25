import pytest
from unittest.mock import MagicMock
import numpy as np

from cv.detection.base import BBox, Detection
from cv.tracking.byte_tracker import ByteTracker

@pytest.fixture
def byte_tracker():
    config = {
        "tracker": {
            "type": "bytetrack",
            "track_thresh": 0.25,
            "track_buffer": 30,
            "match_thresh": 0.8
        }
    }
    return ByteTracker(config)

def test_tracker_empty_update(byte_tracker):
    tracked = byte_tracker.update([])
    assert len(tracked) == 0

def test_tracker_assigns_ids(byte_tracker):
    # Frame 1 — tracks are tentative (min_hits=2)
    d1 = Detection(bbox=BBox(0, 0, 10, 10), class_id=0, class_name="person", confidence=0.9, frame_id=1)
    d2 = Detection(bbox=BBox(20, 20, 30, 30), class_id=0, class_name="person", confidence=0.9, frame_id=1)
    byte_tracker.update([d1, d2])  # Frame 1 — tentative, not returned yet
    
    # Frame 2 — tracks now confirmed (min_hits satisfied)
    d1_f2 = Detection(bbox=BBox(1, 1, 11, 11), class_id=0, class_name="person", confidence=0.9, frame_id=2)
    d2_f2 = Detection(bbox=BBox(21, 21, 31, 31), class_id=0, class_name="person", confidence=0.9, frame_id=2)
    tracked_1 = byte_tracker.update([d1_f2, d2_f2])
    assert len(tracked_1) == 2
    
    id1, id2 = tracked_1[0].track_id, tracked_1[1].track_id
    assert id1 is not None
    assert id2 is not None
    assert id1 != id2
    
    # Frame 3 — slightly moved — same IDs should persist
    d1_f3 = Detection(bbox=BBox(2, 2, 12, 12), class_id=0, class_name="person", confidence=0.9, frame_id=3)
    d2_f3 = Detection(bbox=BBox(22, 22, 32, 32), class_id=0, class_name="person", confidence=0.9, frame_id=3)
    tracked_2 = byte_tracker.update([d1_f3, d2_f3])
    assert len(tracked_2) == 2
    
    # Same set of IDs should be maintained
    set_ids_1 = {t.track_id for t in tracked_1}
    set_ids_2 = {t.track_id for t in tracked_2}
    assert set_ids_1 == set_ids_2
    
def test_tracker_drops_lost_track(byte_tracker):
    # Frame 1 and 2 (to confirm the track)
    d1 = Detection(bbox=BBox(0, 0, 10, 10), class_id=0, class_name="person", confidence=0.9, frame_id=1)
    byte_tracker.update([d1])
    d1_f2 = Detection(bbox=BBox(0, 0, 10, 10), class_id=0, class_name="person", confidence=0.9, frame_id=2)
    tracked_2 = byte_tracker.update([d1_f2])
    assert len(tracked_2) == 1
    id1 = tracked_2[0].track_id
    
    # Missing from frames 3 to 40 (exceeds track_buffer=30)
    for i in range(3, 42):
        byte_tracker.update([])
        
    # Re-appears at frame 42 and 43 (needs 2 frames to confirm a new track)
    d1_f42 = Detection(bbox=BBox(0, 0, 10, 10), class_id=0, class_name="person", confidence=0.9, frame_id=42)
    byte_tracker.update([d1_f42])
    
    d1_f43 = Detection(bbox=BBox(0, 0, 10, 10), class_id=0, class_name="person", confidence=0.9, frame_id=43)
    tracked_3 = byte_tracker.update([d1_f43])
    
    assert len(tracked_3) == 1
    id2 = tracked_3[0].track_id
    # Since it was missing for > 30 frames, it should get a NEW id
    assert id1 != id2

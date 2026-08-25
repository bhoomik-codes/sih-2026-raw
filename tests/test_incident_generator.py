"""
tests.test_incident_generator
-----------------------------
Tests for the IncidentGenerator.
"""

import time
from intelligence.events.base import EventSeverity, EventType, SurveillanceEvent
from intelligence.incidents.generator import IncidentGenerator


def make_event(ev_type: EventType, track_id: int) -> SurveillanceEvent:
    return SurveillanceEvent(
        event_type=ev_type,
        severity=EventSeverity.LOW,
        track_id=track_id,
        camera_name="TEST-CAM",
        timestamp=time.time(),
        frame_id=1,
        location=(0,0),
        class_name="person",
        confidence=0.9,
        rule_name="test"
    )

def test_incident_generator_escalation():
    cfg = {
        "incident_engine": {"enabled": True, "escalation_threshold": 50, "cooldown_s": 10.0},
        "risk_engine": {"zone_entry": 30, "line_crossing": 40}
    }
    gen = IncidentGenerator(cfg)
    
    # 30 points -> below threshold (50)
    ev1 = make_event(EventType.ZONE_ENTRY, track_id=1)
    incs = gen.update([ev1])
    assert len(incs) == 0
    
    # +40 points -> 70 total -> above threshold
    ev2 = make_event(EventType.LINE_CROSSING, track_id=1)
    incs = gen.update([ev2])
    assert len(incs) == 1
    assert incs[0].track_id == 1
    assert incs[0].risk_score == 70

def test_incident_generator_cooldown():
    cfg = {
        "incident_engine": {"enabled": True, "escalation_threshold": 20, "cooldown_s": 5.0},
        "risk_engine": {"zone_entry": 30}
    }
    gen = IncidentGenerator(cfg)
    
    # 30 points -> triggers incident
    ev1 = make_event(EventType.ZONE_ENTRY, track_id=2)
    assert len(gen.update([ev1])) == 1
    
    # Same score (30) within cooldown -> no new incident
    ev2 = make_event(EventType.ZONE_EXIT, track_id=2) # 0 points
    assert len(gen.update([ev2])) == 0
    
    # If we hack the internal time of the generator to simulate 6 seconds passing
    gen._last_incident_time[2] -= 6.0
    assert len(gen.update([ev2])) == 1  # Should trigger again due to cooldown expiry

def test_incident_generator_score_increase_bypasses_cooldown():
    cfg = {
        "incident_engine": {"enabled": True, "escalation_threshold": 20, "cooldown_s": 10.0},
        "risk_engine": {"zone_entry": 30, "loitering": 15}
    }
    gen = IncidentGenerator(cfg)
    
    # 30 points
    ev1 = make_event(EventType.ZONE_ENTRY, track_id=3)
    assert len(gen.update([ev1])) == 1
    
    # 45 points -> score increased, should bypass cooldown and alert immediately
    ev2 = make_event(EventType.LOITERING, track_id=3)
    incs = gen.update([ev2])
    assert len(incs) == 1
    assert incs[0].risk_score == 45

def test_cleanup_stale_tracks():
    gen = IncidentGenerator()
    ev1 = make_event(EventType.ZONE_ENTRY, track_id=4)
    gen.update([ev1])
    assert 4 in gen._event_buffer
    
    gen.cleanup_stale_tracks(active_track_ids={5, 6})
    assert 4 not in gen._event_buffer

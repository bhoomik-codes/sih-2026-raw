"""
tests.test_risk_engine
----------------------
Tests for the RiskScorer.
"""

from intelligence.events.base import EventSeverity, EventType, SurveillanceEvent
from intelligence.risk.scorer import RiskScorer


def make_event(ev_type: EventType) -> SurveillanceEvent:
    return SurveillanceEvent(
        event_type=ev_type,
        severity=EventSeverity.LOW,
        track_id=1,
        camera_name="TEST-CAM",
        timestamp=0.0,
        frame_id=1,
        location=(0, 0),
        class_name="person",
        confidence=0.9,
        rule_name="test",
    )


def test_risk_scorer_calculates_sum():
    scorer = RiskScorer()
    # default config: ZONE_ENTRY=30, LINE_CROSSING=40
    events = [make_event(EventType.ZONE_ENTRY), make_event(EventType.LINE_CROSSING)]
    score, sev = scorer.evaluate(events)
    assert score == 70
    assert sev == EventSeverity.HIGH


def test_risk_scorer_critical_threshold():
    scorer = RiskScorer()
    events = [
        make_event(EventType.ZONE_ENTRY),
        make_event(EventType.LINE_CROSSING),
        make_event(EventType.LOITERING),
    ]
    score, sev = scorer.evaluate(events)
    assert score == 85  # 30 + 40 + 15
    assert sev == EventSeverity.CRITICAL


def test_risk_scorer_custom_config():
    cfg = {"zone_entry": 5, "line_crossing": 10}
    scorer = RiskScorer(cfg)
    events = [make_event(EventType.ZONE_ENTRY), make_event(EventType.LINE_CROSSING)]
    score, sev = scorer.evaluate(events)
    assert score == 15
    assert sev == EventSeverity.LOW

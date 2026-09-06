"""
tests.test_alert_frequency
--------------------------
Comprehensive tests for real-time alert frequency, state-aware deduplication,
multi-track isolation, rapid event handling, and incident lifecycle.
"""

import time
import pytest
from httpx import ASGITransport, AsyncClient

from intelligence.events.base import EventSeverity, EventType, SurveillanceEvent
from intelligence.incidents.generator import IncidentGenerator
from apps.backend.main import app, _in_memory_incidents, _in_memory_events, _deleted_camera_ids, _alert_metrics


def make_test_event(
    event_type: EventType,
    track_id: int,
    camera_name: str = "CAM-2726",
    rule_name: str = "line:border_line",
    severity: EventSeverity = EventSeverity.HIGH,
    details: dict = None,
) -> SurveillanceEvent:
    return SurveillanceEvent(
        event_type=event_type,
        severity=severity,
        track_id=track_id,
        camera_name=camera_name,
        timestamp=time.time(),
        frame_id=1,
        location=(100.0, 200.0),
        class_name="person",
        confidence=0.95,
        rule_name=rule_name,
        details=details or {},
    )


# ==============================================================================
# 1. Multi-Track Test (Section 12)
# ==============================================================================
def test_multi_track_no_mutual_suppression():
    """Two different tracks triggering the same rule must both generate incidents."""
    cfg = {
        "incident_engine": {"enabled": True, "escalation_threshold": 30, "cooldown_s": 10.0},
        "risk_engine": {"line_crossing": 40},
    }
    gen = IncidentGenerator(cfg)

    # Track 104 crosses border line
    ev104 = make_test_event(
        EventType.LINE_CROSSING,
        track_id=104,
        rule_name="line:border_line",
        severity=EventSeverity.CRITICAL,
        details={"line": "border_line", "direction": "AB"},
    )
    incs104 = gen.update([ev104])
    assert len(incs104) == 1
    assert incs104[0].track_id == 104
    assert incs104[0].incident_type == "LINE_CROSSING"

    # Track 109 crosses border line immediately after (within 1 second)
    ev109 = make_test_event(
        EventType.LINE_CROSSING,
        track_id=109,
        rule_name="line:border_line",
        severity=EventSeverity.CRITICAL,
        details={"line": "border_line", "direction": "AB"},
    )
    incs109 = gen.update([ev109])
    assert len(incs109) == 1
    assert incs109[0].track_id == 109
    assert incs109[0].incident_type == "LINE_CROSSING"


# ==============================================================================
# 2. Line Crossing Reversal Test (Section 3)
# ==============================================================================
def test_line_crossing_reversal_generates_new_incident():
    """Same track crossing in reverse direction (AB then BA) is a distinct security condition."""
    cfg = {
        "incident_engine": {"enabled": True, "escalation_threshold": 30, "cooldown_s": 10.0},
        "risk_engine": {"line_crossing": 40},
    }
    gen = IncidentGenerator(cfg)

    # Track 104: LEFT -> RIGHT (AB)
    ev_ab = make_test_event(
        EventType.LINE_CROSSING,
        track_id=104,
        rule_name="line:border_line",
        severity=EventSeverity.CRITICAL,
        details={"line": "border_line", "direction": "AB"},
    )
    incs1 = gen.update([ev_ab])
    assert len(incs1) == 1
    assert incs1[0].direction == "AB"

    # Track 104: RIGHT -> LEFT (BA) 2 seconds later
    ev_ba = make_test_event(
        EventType.LINE_CROSSING,
        track_id=104,
        rule_name="line:border_line",
        severity=EventSeverity.CRITICAL,
        details={"line": "border_line", "direction": "BA"},
    )
    incs2 = gen.update([ev_ba])
    assert len(incs2) == 1
    assert incs2[0].direction == "BA"


# ==============================================================================
# 3. Rapid Events Test (Section 13)
# ==============================================================================
def test_rapid_distinct_events_within_cooldown():
    """Different rules/conditions for same track within cooldown generate separate incidents."""
    cfg = {
        "incident_engine": {"enabled": True, "escalation_threshold": 30, "cooldown_s": 10.0},
        "risk_engine": {"line_crossing": 40, "zone_entry": 35},
    }
    gen = IncidentGenerator(cfg)

    # Event 1: Track 104 crosses line
    ev1 = make_test_event(
        EventType.LINE_CROSSING,
        track_id=104,
        rule_name="line:border_line",
        severity=EventSeverity.CRITICAL,
        details={"line": "border_line", "direction": "AB"},
    )
    incs1 = gen.update([ev1])
    assert len(incs1) == 1
    assert incs1[0].incident_type == "LINE_CROSSING"

    # Event 2: Track 104 enters restricted zone (2 seconds later)
    ev2 = make_test_event(
        EventType.ZONE_ENTRY,
        track_id=104,
        rule_name="zone:restricted_zone_a",
        severity=EventSeverity.HIGH,
        details={"zone": "restricted_zone_a"},
    )
    incs2 = gen.update([ev2])
    assert len(incs2) == 1
    assert incs2[0].incident_type == "ZONE_ENTRY"
    assert incs2[0].zone_id == "restricted_zone_a"


# ==============================================================================
# 4. Anti-Flooding Test (Section 15)
# ==============================================================================
def test_same_condition_repeat_does_not_flood_incidents():
    """Identical condition repeating on consecutive frames is debounced without incident spam."""
    cfg = {
        "incident_engine": {"enabled": True, "escalation_threshold": 30, "cooldown_s": 10.0},
        "risk_engine": {"zone_entry": 35},
    }
    gen = IncidentGenerator(cfg)

    ev_initial = make_test_event(
        EventType.ZONE_ENTRY,
        track_id=104,
        rule_name="zone:restricted_zone_a",
        severity=EventSeverity.HIGH,
        details={"zone": "restricted_zone_a"},
    )
    # First entry triggers incident
    assert len(gen.update([ev_initial])) == 1

    # 10 consecutive frames of identical event within cooldown window
    for _ in range(10):
        ev_repeat = make_test_event(
            EventType.ZONE_ENTRY,
            track_id=104,
            rule_name="zone:restricted_zone_a",
            severity=EventSeverity.HIGH,
            details={"zone": "restricted_zone_a"},
        )
        # Should NOT produce new incident
        assert len(gen.update([ev_repeat])) == 0


# ==============================================================================
# 5. Backend State-Aware In-Place Update vs New Incident Test (Section 6 & 11)
# ==============================================================================
@pytest.mark.anyio
async def test_backend_incident_lifecycle_update_and_deduplication():
    """Backend updates active incident in place and creates new incident for new condition."""
    # Clear in-memory state
    _in_memory_incidents.clear()
    _in_memory_events.clear()
    _deleted_camera_ids.clear()
    for k in _alert_metrics:
        _alert_metrics[k] = 0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register a camera first
        reg_resp = await ac.post("/api/cameras", json={
            "camera_id": "CAM-2726",
            "name": "Border Gate 1",
            "source_type": "stream",
            "source_url": "http://10.0.0.1:8080/video",
        })
        assert reg_resp.status_code == 200

        # Ingest Incident 1: Track 104 Line Crossing AB
        inc1_payload = {
            "incident_id": "INC-104-LC",
            "camera_id": "CAM-2726",
            "track_id": 104,
            "incident_type": "LINE_CROSSING",
            "rule_name": "line:border_line",
            "line_id": "border_line",
            "direction": "AB",
            "severity": "CRITICAL",
            "risk_score": 100,
            "summary": "Line Crossing: Track #104 crossed border_line (AB)",
        }
        r1 = await ac.post("/api/edge/incident", json=inc1_payload)
        assert r1.status_code == 200
        data1 = r1.json()
        assert data1["status"] == "ok"
        assert _alert_metrics["incidents_created"] == 1

        # Ingest Incident 2: Track 109 Line Crossing AB (different track) -> NEW INCIDENT
        inc2_payload = {
            "incident_id": "INC-109-LC",
            "camera_id": "CAM-2726",
            "track_id": 109,
            "incident_type": "LINE_CROSSING",
            "rule_name": "line:border_line",
            "line_id": "border_line",
            "direction": "AB",
            "severity": "CRITICAL",
            "risk_score": 100,
            "summary": "Line Crossing: Track #109 crossed border_line (AB)",
        }
        r2 = await ac.post("/api/edge/incident", json=inc2_payload)
        assert r2.status_code == 200
        assert r2.json()["status"] == "ok"
        assert _alert_metrics["incidents_created"] == 2

        # Ingest Incident 3: Repeat of Track 104 Line Crossing AB -> UPDATED IN PLACE!
        inc3_payload = {
            "incident_id": "INC-104-LC-REPEAT",
            "camera_id": "CAM-2726",
            "track_id": 104,
            "incident_type": "LINE_CROSSING",
            "rule_name": "line:border_line",
            "line_id": "border_line",
            "direction": "AB",
            "severity": "CRITICAL",
            "risk_score": 100,
            "summary": "Line Crossing: Track #104 crossed border_line (AB)",
        }
        r3 = await ac.post("/api/edge/incident", json=inc3_payload)
        assert r3.status_code == 200
        data3 = r3.json()
        assert data3["status"] == "updated"
        assert data3["incident_id"] == "INC-104-LC"  # Updated original incident
        assert _alert_metrics["incidents_updated"] == 1
        assert _alert_metrics["incidents_created"] == 2  # Not incremented!

        # Ingest Incident 4: Track 104 Line Crossing in BA direction -> NEW INCIDENT!
        inc4_payload = {
            "incident_id": "INC-104-LC-BA",
            "camera_id": "CAM-2726",
            "track_id": 104,
            "incident_type": "LINE_CROSSING",
            "rule_name": "line:border_line",
            "line_id": "border_line",
            "direction": "BA",
            "severity": "CRITICAL",
            "risk_score": 100,
            "summary": "Line Crossing: Track #104 crossed border_line (BA)",
        }
        r4 = await ac.post("/api/edge/incident", json=inc4_payload)
        assert r4.status_code == 200
        assert r4.json()["status"] == "ok"
        assert _alert_metrics["incidents_created"] == 3

        # Resolve INC-104-LC
        resolve_resp = await ac.post("/api/incidents/INC-104-LC/resolve")
        assert resolve_resp.status_code == 200
        assert resolve_resp.json()["status"] == "RESOLVED"

        # Now send Track 104 Line Crossing AB again -> Since old is RESOLVED, allows NEW incident!
        inc5_payload = {
            "incident_id": "INC-104-LC-NEW",
            "camera_id": "CAM-2726",
            "track_id": 104,
            "incident_type": "LINE_CROSSING",
            "rule_name": "line:border_line",
            "line_id": "border_line",
            "direction": "AB",
            "severity": "CRITICAL",
            "risk_score": 100,
            "summary": "Line Crossing: Track #104 crossed border_line (AB)",
        }
        r5 = await ac.post("/api/edge/incident", json=inc5_payload)
        assert r5.status_code == 200
        assert r5.json()["status"] == "ok"
        assert _alert_metrics["incidents_created"] == 4

        # Verify debug metrics endpoint
        metrics_resp = await ac.get("/api/debug/alert-metrics")
        assert metrics_resp.status_code == 200
        m = metrics_resp.json()
        assert m["incidents_created"] == 4
        assert m["incidents_updated"] == 1


# ==============================================================================
# 6. Camera Deletion Regression Test (Section 17)
# ==============================================================================
@pytest.mark.anyio
async def test_camera_deletion_ghost_rejection():
    """Deleted camera events and incidents must be rejected with 'camera_deleted'."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register CAM-99
        await ac.post("/api/cameras", json={
            "camera_id": "CAM-99",
            "name": "Gate 99",
            "source_type": "file",
            "source_url": "test.mp4",
        })

        # Delete CAM-99
        del_resp = await ac.delete("/api/cameras/CAM-99")
        assert del_resp.status_code == 200

        # Attempt ghost event
        evt_resp = await ac.post("/api/edge/event", json={
            "camera_name": "CAM-99",
            "event_type": "ZONE_ENTRY",
            "track_id": 999,
        })
        assert evt_resp.status_code == 200
        assert evt_resp.json() == {
            "status": "rejected",
            "reason": "camera_deleted",
            "camera_id": "CAM-99",
        }

        # Attempt ghost incident
        inc_resp = await ac.post("/api/edge/incident", json={
            "camera_name": "CAM-99",
            "incident_type": "LINE_CROSSING",
            "track_id": 999,
        })
        assert inc_resp.status_code == 200
        assert inc_resp.json() == {
            "status": "rejected",
            "reason": "camera_deleted",
            "camera_id": "CAM-99",
        }

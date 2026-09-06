"""
intelligence.incidents.generator
--------------------------------
Generates Incidents from a stream of SurveillanceEvents.

This component buffers events by track_id, evaluates them through the RiskScorer,
and issues an Incident if the risk score exceeds a configurable escalation threshold.
Includes a cooldown mechanism so that we don't spam the same incident continuously
unless the score increases or a new critical event occurs.
"""

import logging
import time
from collections import defaultdict
from typing import Dict, List

from intelligence.events.base import EventType, SurveillanceEvent
from intelligence.incidents.base import Incident
from intelligence.risk.scorer import RiskScorer

logger = logging.getLogger(__name__)


class IncidentGenerator:
    """
    Correlates events and generates incidents.
    """

    def __init__(self, config: dict = None) -> None:
        self._config = config or {}
        inc_cfg = self._config.get("incident_engine") or self._config.get("incidents") or {}

        self._enabled = bool(inc_cfg.get("enabled", True))
        self._escalation_threshold = int(inc_cfg.get("escalation_threshold", 50))
        self._cooldown_s = float(inc_cfg.get("cooldown_s", 10.0))

        risk_cfg = self._config.get("risk_engine", {})
        self._scorer = RiskScorer(risk_cfg)

        # Buffer: track_id -> List of events
        self._event_buffer: Dict[int, List[SurveillanceEvent]] = defaultdict(list)

        # State tracking to avoid spamming
        # track_id -> last incident score
        self._last_score: Dict[int, int] = {}
        # track_id -> timestamp of last incident generated
        self._last_incident_time: Dict[int, float] = {}
        # track_id -> timestamp last active
        self._last_seen: Dict[int, float] = {}
        # condition_key -> timestamp of last incident for this condition
        self._last_condition_time: Dict[str, float] = {}

    @staticmethod
    def _condition_key(ev: SurveillanceEvent) -> str:
        ev_type = ev.event_type.name if hasattr(ev.event_type, "name") else str(ev.event_type)
        rule = getattr(ev, "rule_name", "")
        details = getattr(ev, "details", {}) or {}
        target = details.get("line") or details.get("zone") or ""
        direction = details.get("direction") or ""
        return f"{ev.track_id}|{rule}|{ev_type}|{target}|{direction}"

    def update(self, events: List[SurveillanceEvent]) -> List[Incident]:
        """
        Ingest new events and return any generated incidents.
        """
        if not self._enabled or not events:
            return []

        now = time.time()

        # 1. Update buffer with new events
        updated_tracks = set()
        new_conditions_by_track: Dict[int, List[str]] = defaultdict(list)
        for ev in events:
            self._event_buffer[ev.track_id].append(ev)
            self._last_seen[ev.track_id] = now
            updated_tracks.add(ev.track_id)
            c_key = self._condition_key(ev)
            new_conditions_by_track[ev.track_id].append(c_key)

        incidents: List[Incident] = []

        # 2. Evaluate risk for tracks that received new events
        for tid in updated_tracks:
            track_events = self._event_buffer[tid]
            score, severity = self._scorer.evaluate(track_events)

            # Check escalation threshold
            if score >= self._escalation_threshold:
                last_score = self._last_score.get(tid, 0)
                last_time = self._last_incident_time.get(tid, 0.0)

                # Check if this update brings a genuinely new security condition
                # (e.g. crossing a different line, entering a zone, crossing opposite direction)
                new_evs = [
                    ev for ev in events
                    if ev.track_id == tid and ev.event_type != getattr(EventType, "ZONE_EXIT", None)
                ]
                has_new_condition = bool(new_evs) and any(
                    (now - self._last_condition_time.get(self._condition_key(e), 0.0)) > self._cooldown_s
                    for e in new_evs
                )

                # Generate incident if:
                # 1) A genuinely new condition occurred, OR
                # 2) The cumulative score escalated, OR
                if (
                    (last_score == 0 and score >= self._escalation_threshold)
                    or has_new_condition
                    or (now - last_time) > self._cooldown_s
                ):
                    latest_ev = track_events[-1]
                    ev_type = (
                        latest_ev.event_type.name
                        if hasattr(latest_ev.event_type, "name")
                        else str(latest_ev.event_type)
                    )
                    rule_name = getattr(latest_ev, "rule_name", "")
                    details = getattr(latest_ev, "details", {}) or {}
                    line_id = str(details.get("line", ""))
                    zone_id = str(details.get("zone", ""))
                    direction = str(details.get("direction", ""))

                    if ev_type == "LINE_CROSSING":
                        summary_text = f"Line Crossing: Track #{tid} crossed {line_id or rule_name} ({direction or 'any'})"
                    elif ev_type == "ZONE_ENTRY":
                        summary_text = f"Zone Intrusion: Track #{tid} entered {zone_id or rule_name}"
                    elif ev_type == "FACE_IDENTIFIED_INTRUDER":
                        summary_text = f"Intruder Identified: Track #{tid} ({details.get('name', 'Unknown')})"
                    elif ev_type == "LOITERING":
                        summary_text = f"Loitering Alert: Track #{tid} in {zone_id or rule_name}"
                    else:
                        summary_text = f"{ev_type}: Track #{tid} on {rule_name}"

                    inc = Incident(
                        track_id=tid,
                        risk_score=score,
                        severity=severity,
                        triggering_events=list(track_events),
                        camera_name=latest_ev.camera_name,
                        description=summary_text,
                        incident_type=ev_type,
                        rule_name=rule_name,
                        line_id=line_id,
                        zone_id=zone_id,
                        direction=direction,
                        event_count=len(track_events),
                        condition_key=self._condition_key(latest_ev),
                    )

                    incidents.append(inc)

                    # Update state
                    self._last_score[tid] = score
                    self._last_incident_time[tid] = now
                    for e in new_evs:
                        self._last_condition_time[self._condition_key(e)] = now

                    logger.warning("INCIDENT GENERATED: %s", inc)

        return incidents

    def cleanup_stale_tracks(self, active_track_ids: set) -> None:
        """
        Remove tracks from the buffer that are no longer active.
        """
        stale = [tid for tid in list(self._event_buffer.keys()) if tid not in active_track_ids]
        for tid in stale:
            self._event_buffer.pop(tid, None)
            self._last_score.pop(tid, None)
            self._last_incident_time.pop(tid, None)
            self._last_seen.pop(tid, None)

        # Cleanup condition timestamps for stale tracks
        stale_conditions = [
            ck for ck in list(self._last_condition_time.keys())
            if any(ck.startswith(f"{tid}|") for tid in stale)
        ]
        for ck in stale_conditions:
            self._last_condition_time.pop(ck, None)

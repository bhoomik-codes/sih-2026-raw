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

from intelligence.events.base import SurveillanceEvent
from intelligence.incidents.base import Incident
from intelligence.risk.scorer import RiskScorer

logger = logging.getLogger(__name__)


class IncidentGenerator:
    """
    Correlates events and generates incidents.
    """

    def __init__(self, config: dict = None) -> None:
        self._config = config or {}
        inc_cfg = self._config.get("incident_engine", {})

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

    def update(self, events: List[SurveillanceEvent]) -> List[Incident]:
        """
        Ingest new events and return any generated incidents.
        """
        if not self._enabled or not events:
            return []

        now = time.time()

        # 1. Update buffer with new events
        updated_tracks = set()
        for ev in events:
            self._event_buffer[ev.track_id].append(ev)
            self._last_seen[ev.track_id] = now
            updated_tracks.add(ev.track_id)

        incidents: List[Incident] = []

        # 2. Evaluate risk for tracks that received new events
        for tid in updated_tracks:
            track_events = self._event_buffer[tid]
            score, severity = self._scorer.evaluate(track_events)

            # Check escalation threshold
            if score >= self._escalation_threshold:
                last_score = self._last_score.get(tid, 0)
                last_time = self._last_incident_time.get(tid, 0.0)

                # Only generate if the score went up, or cooldown expired
                if score > last_score or (now - last_time) > self._cooldown_s:
                    # Create the incident
                    inc = Incident(
                        track_id=tid,
                        risk_score=score,
                        severity=severity,
                        triggering_events=list(track_events),  # copy of current events
                        camera_name=track_events[-1].camera_name,
                        description=f"Risk Score {score} reached. Events: {len(track_events)}",
                    )

                    incidents.append(inc)

                    # Update state
                    self._last_score[tid] = score
                    self._last_incident_time[tid] = now

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

"""
intelligence.incidents.base
---------------------------
Core data structures for incidents.

An Incident is an escalated collection of SurveillanceEvents that have surpassed
a defined risk threshold.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import List

from intelligence.events.base import EventSeverity, SurveillanceEvent


@dataclass
class Incident:
    """
    Represents a significant security concern composed of one or more events.

    Attributes:
        incident_id:       Unique identifier for the incident.
        track_id:          The tracked object associated with this incident.
        risk_score:        The computed risk score (0-100+).
        severity:          The overall severity of the incident.
        triggering_events: The events that contributed to this incident.
        timestamp:         Unix timestamp of when the incident was generated.
        camera_name:       The camera where this occurred.
        description:       A human-readable summary of what happened.
    """
    incident_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    track_id: int = -1
    risk_score: int = 0
    severity: EventSeverity = EventSeverity.LOW
    triggering_events: List[SurveillanceEvent] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    camera_name: str = ""
    description: str = ""

    def __repr__(self) -> str:
        ts = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        ev_types = [e.event_type.name for e in self.triggering_events]
        return (
            f"[{ts}] INCIDENT #{self.incident_id} | Track #{self.track_id} | "
            f"Score: {self.risk_score} ({self.severity.name}) | Events: {ev_types}"
        )

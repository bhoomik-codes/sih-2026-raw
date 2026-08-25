"""
intelligence.risk.scorer
------------------------
Calculates a cumulative risk score based on an object's event history.
"""

from typing import Dict, List, Tuple

from intelligence.events.base import EventSeverity, EventType, SurveillanceEvent


class RiskScorer:
    """
    Evaluates a list of events to produce a risk score and severity.
    
    Default point values can be overridden via configuration.
    """

    def __init__(self, config: dict = None) -> None:
        cfg = config or {}
        # Default mapping of event types to risk points
        self._point_map: Dict[EventType, int] = {
            EventType.ZONE_ENTRY: int(cfg.get("zone_entry", 30)),
            EventType.LINE_CROSSING: int(cfg.get("line_crossing", 40)),
            EventType.LOITERING: int(cfg.get("loitering", 15)),
            EventType.ZONE_EXIT: int(cfg.get("zone_exit", 0)),
            EventType.WRONG_DIRECTION: int(cfg.get("wrong_direction", 20)),
            EventType.VEHICLE_ANPR: int(cfg.get("vehicle_anpr", 0)),
        }

    def evaluate(self, events: List[SurveillanceEvent]) -> Tuple[int, EventSeverity]:
        """
        Calculate total risk score and derive the overall severity.

        Args:
            events: The list of events associated with a single track.

        Returns:
            A tuple of (total_score, severity)
        """
        total_score = sum(self._point_map.get(e.event_type, 0) for e in events)
        
        # Override severity if any event is critical (e.g. ANPR Match)
        if any(e.severity == EventSeverity.CRITICAL for e in events):
            return max(total_score, 100), EventSeverity.CRITICAL

        if total_score >= 80:
            severity = EventSeverity.CRITICAL
        elif total_score >= 50:
            severity = EventSeverity.HIGH
        elif total_score >= 20:
            severity = EventSeverity.MEDIUM
        else:
            severity = EventSeverity.LOW

        return total_score, severity

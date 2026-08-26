import { useState, useEffect, useCallback } from 'react';
import { SurveillanceEvent } from '../types/event';
import { getEvents } from '../api/events';

const MAX_TIMELINE_EVENTS = 150;

export function useEvents() {
  const [events, setEvents] = useState<SurveillanceEvent[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEvents = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getEvents({ limit: 50 });
      setEvents(data);
    } catch (err: any) {
      setError(err.message || 'Unable to load events');
      setEvents([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const handleNewEvent = useCallback((newEvent: SurveillanceEvent) => {
    setEvents((prev) => {
      // Prevent duplicates by event_id or signature
      const eventKey = newEvent.event_id || `${newEvent.track_id}-${newEvent.timestamp}-${newEvent.event_type}`;
      const exists = prev.some((e) => (e.event_id || `${e.track_id}-${e.timestamp}-${e.event_type}`) === eventKey);
      if (exists) return prev;
      return [newEvent, ...prev].slice(0, MAX_TIMELINE_EVENTS);
    });
  }, []);

  return {
    events,
    isLoading,
    error,
    refresh: fetchEvents,
    handleNewEvent,
  };
}

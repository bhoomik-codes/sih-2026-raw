import { useEffect, useRef, useState, useCallback } from 'react';
import { SurveillanceEvent } from '../types/event';
import { Incident } from '../types/incident';
import { SystemMetrics } from '../types/metrics';

export type WebSocketStatus = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' | 'ERROR';

interface UseWebSocketOptions {
  onEvent?: (event: SurveillanceEvent) => void;
  onIncident?: (incident: Incident) => void;
  onMetrics?: (metrics: SystemMetrics) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const [status, setStatus] = useState<WebSocketStatus>('DISCONNECTED');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);
  const seenEventIdsRef = useRef<Set<string>>(new Set());

  const optionsRef = useRef(options);
  optionsRef.current = options;

  const connect = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws`;

    setStatus('CONNECTING');

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus('CONNECTED');
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const type = message.type || message.event_type || 'unknown';
          const payload = message.data || message;

          if (type === 'event' || message.event_type) {
            const ev: SurveillanceEvent = payload;
            const eventKey = ev.event_id || `${ev.track_id}-${ev.timestamp}-${ev.event_type}`;
            if (!seenEventIdsRef.current.has(eventKey)) {
              seenEventIdsRef.current.add(eventKey);
              if (seenEventIdsRef.current.size > 500) {
                // Clear old IDs
                seenEventIdsRef.current.clear();
              }
              optionsRef.current.onEvent?.(ev);
            }
          } else if (type === 'incident' || message.incident_id) {
            const inc: Incident = payload;
            optionsRef.current.onIncident?.(inc);
          } else if (type === 'metrics' || message.inference_fps !== undefined) {
            const m: SystemMetrics = payload;
            optionsRef.current.onMetrics?.(m);
          }
        } catch {
          // Non-JSON message or unparseable frame
        }
      };

      ws.onclose = () => {
        setStatus('DISCONNECTED');
        wsRef.current = null;
        scheduleReconnect();
      };

      ws.onerror = () => {
        setStatus('ERROR');
        wsRef.current = null;
      };
    } catch {
      setStatus('ERROR');
      scheduleReconnect();
    }
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    reconnectTimeoutRef.current = setTimeout(() => {
      setStatus('RECONNECTING');
      connect();
    }, 5000);
  }, [connect]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return {
    status,
    isConnected: status === 'CONNECTED',
    reconnect: connect,
  };
}

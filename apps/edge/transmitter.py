"""
apps.edge.transmitter
----------------------
Real-time WebSocket transmitter for the IBVAP Edge Processing Node.

Transmits live surveillance events, active incidents, camera telemetry,
and system metrics to the FastAPI Command Center backend (apps.backend.main).

Features:
- Non-blocking queue: inference loop never blocks on network I/O
- Resilient background worker with automatic reconnect and exponential backoff
- JSON payload serialization with schema compatibility
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import websocket

    HAS_WEBSOCKET_CLIENT = True
except ImportError:
    HAS_WEBSOCKET_CLIENT = False


class EdgeTransmitter:
    """
    Background worker that streams edge events and telemetry to the backend.
    """

    def __init__(
        self,
        backend_url: str = "ws://localhost:8000/ws",
        node_id: str = "EDGE-NODE-01",
        max_queue_size: int = 500,
    ) -> None:
        self._url = backend_url
        self._node_id = node_id
        self._queue: queue.Queue[Dict[str, Any]] = queue.Queue(maxsize=max_queue_size)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._ws: Optional[Any] = None
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def start(self) -> "EdgeTransmitter":
        """Start the background transmission thread."""
        if not HAS_WEBSOCKET_CLIENT:
            logger.warning(
                "websocket-client package is not installed. "
                "Edge events will be queued locally. Install with: pip install websocket-client"
            )
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._worker_loop,
            name="EdgeTransmitter-Worker",
            daemon=True,
        )
        self._thread.start()
        logger.info("EdgeTransmitter started -> backend: %s", self._url)
        return self

    def stop(self) -> None:
        """Stop background transmitter and close active connection."""
        self._stop_event.set()
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("EdgeTransmitter stopped.")

    def emit_event(self, event_data: Dict[str, Any]) -> None:
        """Enqueue a surveillance event for transmission."""
        payload = {
            "type": "edge_event",
            "node_id": self._node_id,
            "timestamp": time.time(),
            "data": event_data,
        }
        self._enqueue(payload)

    def emit_incident(self, incident_data: Dict[str, Any]) -> None:
        """Enqueue an incident alert for transmission."""
        payload = {
            "type": "edge_incident",
            "node_id": self._node_id,
            "timestamp": time.time(),
            "data": incident_data,
        }
        self._enqueue(payload)

    def emit_metrics(self, metrics_data: Dict[str, Any]) -> None:
        """Enqueue inference metrics & FPS telemetry."""
        payload = {
            "type": "edge_metrics",
            "node_id": self._node_id,
            "timestamp": time.time(),
            "data": metrics_data,
        }
        self._enqueue(payload)

    def emit_heartbeat(
        self,
        camera_id: str,
        status: str = "ONLINE",
        fps: float = 0.0,
        stream_url: Optional[str] = None,
    ) -> None:
        """Enqueue camera node heartbeat."""
        data = {
            "camera_id": camera_id,
            "status": status,
            "fps": fps,
        }
        if stream_url:
            data["stream_url"] = stream_url
        payload = {
            "type": "edge_heartbeat",
            "node_id": self._node_id,
            "timestamp": time.time(),
            "data": data,
        }
        self._enqueue(payload)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enqueue(self, item: Dict[str, Any]) -> None:
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            # Drop oldest item to prevent memory growth under network partition
            try:
                _ = self._queue.get_nowait()
                self._queue.put_nowait(item)
            except Exception:
                pass

    def _worker_loop(self) -> None:
        retry_delay = 1.0
        while not self._stop_event.is_set():
            if not HAS_WEBSOCKET_CLIENT:
                time.sleep(2.0)
                continue

            try:
                logger.debug("Connecting to Command Center WebSocket: %s", self._url)
                ws = websocket.WebSocket()
                ws.settimeout(5.0)
                ws.connect(self._url)
                self._ws = ws
                self._is_connected = True
                retry_delay = 1.0
                logger.info("Connected to Command Center WebSocket at %s", self._url)

                # Send initial handshake
                handshake = {
                    "type": "edge_handshake",
                    "node_id": self._node_id,
                    "timestamp": time.time(),
                }
                ws.send(json.dumps(handshake))

                # Flush loop
                while not self._stop_event.is_set():
                    try:
                        msg = self._queue.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    try:
                        ws.send(json.dumps(msg))
                    except Exception as send_err:
                        logger.warning("WebSocket send failed: %s. Reconnecting...", send_err)
                        # Re-enqueue item
                        self._enqueue(msg)
                        break

            except Exception as conn_err:
                self._is_connected = False
                logger.debug(
                    "WebSocket connection attempt failed: %s. Retrying in %.1fs...",
                    conn_err,
                    retry_delay,
                )
                self._stop_event.wait(retry_delay)
                retry_delay = min(15.0, retry_delay * 1.5)
            finally:
                self._is_connected = False
                if self._ws:
                    try:
                        self._ws.close()
                    except Exception:
                        pass
                    self._ws = None

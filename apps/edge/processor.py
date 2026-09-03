"""
apps.edge.processor
---------------------
EdgeProcessor — the central inference loop for Phases 1-3.

Pipeline (per frame):
    1. Read frame from VideoSource (latest-frame queue)
    2. Apply preprocessing (ROI mask → resize)
    3. Every N frames: run detector → List[Detection]
    4. Run tracker → persistent track IDs + trajectory history
    5. Run EventEngine → zone/fence/loitering events
    6. Run IncidentGenerator → risk scoring + incident escalation
    7. Annotate frame: bboxes, track IDs, zone overlays, event/incident alerts
    8. Display via OpenCV window (optional)
    9. Write annotated frame to output video (optional)
    10. Collect and print metrics
    11. Graceful shutdown on KeyboardInterrupt / stop()
"""

from __future__ import annotations

import logging
import socket
import time
from typing import List, Optional

import cv2
import numpy as np

from apps.edge.metrics import MetricsCollector
from apps.edge.streamer import MJPEGStreamer
from apps.edge.transmitter import EdgeTransmitter
from apps.edge.video_source import Frame, VideoSource
from cv.detection.base import Detection, DetectorBase
from cv.face.face_detector import FaceDetector
from cv.face.recognition_engine import FaceIdentity, FaceRecognitionEngine, UNKNOWN_IDENTITY
from cv.preprocessing.frame_prep import build_preprocessing_pipeline
from cv.tracking.byte_tracker import ByteTracker
from intelligence.anpr.engine import ANPREngine
from intelligence.events.base import EventType, SurveillanceEvent
from intelligence.events.engine import EventEngine
from intelligence.incidents.base import Incident
from intelligence.incidents.generator import IncidentGenerator

logger = logging.getLogger(__name__)

# Annotation colours per class — BGR format
_CLASS_COLOURS: dict[str, tuple[int, int, int]] = {
    "person": (0, 255, 0),  # Green
    "car": (255, 165, 0),  # Orange
    "motorcycle": (255, 0, 255),  # Magenta
    "bus": (0, 165, 255),  # Orange-ish
    "truck": (0, 0, 255),  # Red
}
_DEFAULT_COLOUR = (200, 200, 200)  # Grey for unknown classes


class EdgeProcessor:
    """
    Phase 1 inference loop: video → detection → annotation → display.

    Args:
        video_source:  A started VideoSource instance.
                       NOTE: source is started INSIDE processor.run(), after warmup.
                       This prevents short video files being consumed during GPU init.
        detector:      A loaded DetectorBase implementation.
        config:        Full config dict (from YAML). Reads:
                         processor.inference_every_n_frames  (default: 3)
                         processor.display                   (default: True)
                         processor.save_annotated            (default: False)
                         processor.output_video_path         (default: None)
                         processor.metrics_print_every_n     (default: 30)
                         output.metrics_csv                  (default: None)
    """

    def __init__(
        self,
        video_source: VideoSource,
        detector: DetectorBase,
        config: dict,
    ) -> None:
        self._source = video_source
        self._detector = detector
        self._config = config

        # --- Tracker ---
        tracker_type = config.get("tracker", {}).get("type", "bytetrack")
        if tracker_type == "bytetrack":
            self._tracker = ByteTracker(config)
        else:
            self._tracker = None

        # --- Event Engine (Phase 3) ---
        cam_name = config.get("camera", {}).get("name", "CAM-01")
        self._event_engine = EventEngine(config, cam_name)

        # --- Incident Engine (Phase 4) ---
        self._incident_generator = IncidentGenerator(config)

        # --- ANPR Engine (Phase 5) ---
        self._anpr_engine = ANPREngine(config, cam_name)

        # --- Face Recognition Engine ---
        face_cfg = config.get("face_recognition", {})
        self._face_recognition_enabled: bool = bool(face_cfg.get("enabled", True))
        if self._face_recognition_enabled:
            backend_http_url = face_cfg.get("backend_url", "http://localhost:8000")
            poll_interval = float(face_cfg.get("poll_interval_s", 30.0))
            match_threshold = float(face_cfg.get("match_threshold", 0.40))
            self._face_detector = FaceDetector(
                min_confidence=float(face_cfg.get("min_face_confidence", 0.5))
            )
            self._face_engine = FaceRecognitionEngine(
                backend_url=backend_http_url,
                poll_interval_s=poll_interval,
                match_threshold=match_threshold,
            )
        else:
            self._face_detector = None
            self._face_engine = None

        # Per-track recognized identities (reset on new detections)
        self._recognized_tracks: dict[int, FaceIdentity] = {}
        # Tracks for which an intruder alert has already been emitted this session
        self._alerted_intruder_tracks: set[int] = set()

        # --- Processor settings ---
        # Merge output + processor so CLI --stream-port does not hide output.display
        proc = {**config.get("output", {}), **config.get("processor", {})}
        self._inference_every_n: int = int(
            config.get("detector", {}).get("inference_every_n_frames", 3)
        )
        self._display: bool = bool(proc.get("display", True))
        self._save_annotated: bool = bool(proc.get("save_annotated", False))
        self._output_video_path: Optional[str] = proc.get("output_video_path", None)
        self._metrics_print_every_n: int = int(proc.get("metrics_print_every_n", 30))
        self._window_name: str = f"IBVAP – {self._source.name}"

        # --- Streaming ---
        stream_port = proc.get("stream_port")
        if stream_port:
            self._streamer = MJPEGStreamer(port=int(stream_port))
            self._source._streamer = self._streamer
        else:
            self._streamer = None

        # --- Preprocessing pipeline ---
        self._preprocess = build_preprocessing_pipeline(config)

        # --- Metrics ---
        csv_path = config.get("output", {}).get("metrics_csv", None)
        self._metrics = MetricsCollector(csv_path=csv_path)

        # --- Backend WebSocket Transmitter (Phase 9) ---
        backend_ws_url = proc.get("backend_ws_url") or config.get("transmitter", {}).get(
            "backend_ws_url", "ws://localhost:8000/ws"
        )
        enable_tx = proc.get(
            "enable_transmitter", config.get("transmitter", {}).get("enabled", True)
        )
        if enable_tx:
            self._transmitter: Optional[EdgeTransmitter] = EdgeTransmitter(
                backend_url=backend_ws_url,
                node_id=cam_name,
            )
        else:
            self._transmitter = None

        # --- Internal state ---
        self._running: bool = False
        self._loop_frame_count: int = 0  # Frames through the inference loop
        self._last_detections: List[Detection] = []
        self._last_events: List[SurveillanceEvent] = []
        self._active_incidents: List[Incident] = []
        self._video_writer: Optional[cv2.VideoWriter] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Start the inference loop. Blocks until stop() is called or
        the video source is exhausted.

        Handles graceful shutdown on KeyboardInterrupt.
        """
        self._running = True
        logger.info(
            "EdgeProcessor starting  inference_every=%d  display=%s",
            self._inference_every_n,
            self._display,
        )

        # Warmup: pre-allocate GPU memory before the real loop.
        # We start the video source AFTER warmup so short files
        # are not consumed during the ~13s GPU init time.
        logger.info("Running detector warmup...")
        self._detector.warmup()
        logger.info("Warmup complete.")

        # Start the camera feed now that warmup is done
        self._source.start()

        if self._streamer:
            self._streamer.start()

        if self._transmitter:
            self._transmitter.start()

        if self._face_engine:
            self._face_engine.start()

        import threading
        self._poller_thread = threading.Thread(target=self._poll_config_loop, daemon=True)
        self._poller_thread.start()

        try:
            self._loop()
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt — shutting down.")
        finally:
            self._shutdown()

    def _poll_config_loop(self):
        """Poll the backend for zone and tripwire updates every 5 seconds."""
        import requests
        backend_url = self._config.get("face_recognition", {}).get("backend_url", "http://127.0.0.1:8001")
        api_url = f"{backend_url}/api/cameras/{self._source.name}"
        
        while self._running:
            try:
                resp = requests.get(api_url, timeout=2.0)
                if resp.status_code == 200:
                    data = resp.json()
                    
                    if data.get("status") == "OFFLINE":
                        logger.info("Command Center marked camera as OFFLINE. Stopping Edge Node...")
                        self.stop()
                        break
                        
                    if "zones" in data:
                        self._event_engine.update_zones(data["zones"])
                    if "virtual_tripwires" in data:
                        self._event_engine.update_lines(data["virtual_tripwires"])
            except Exception as e:
                logger.debug("Failed to poll camera config updates: %s", e)
            
            for _ in range(50):
                if not self._running:
                    break
                time.sleep(0.1)

    def stop(self) -> None:
        """Signal the inference loop to stop after the current frame."""
        self._running = False

    def _lan_ipv4(self) -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _advertised_stream_url(self) -> Optional[str]:
        if not self._streamer:
            return None
        return f"http://{self._lan_ipv4()}:{self._streamer.port}/stream"

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        """Main inference loop — runs until _running is False or source empty."""
        no_frame_streak: int = 0
        max_no_frame_streak: int = 100  # Stop if source is consistently empty

        while self._running:
            frame: Optional[Frame] = self._source.read(timeout=0.05)

            if frame is None:
                no_frame_streak += 1
                if no_frame_streak >= max_no_frame_streak:
                    logger.warning(
                        "No frame received for %d consecutive reads — stopping.",
                        no_frame_streak,
                    )
                    break
                continue

            no_frame_streak = 0
            self._loop_frame_count += 1
            capture_ts = frame.timestamp

            # Preprocessing
            processed = self._preprocess(frame.data)

            # --- Inference (every N frames) ---
            t_inf_start = time.perf_counter()

            if self._loop_frame_count % self._inference_every_n == 0:
                self._last_detections = self._detector.detect(processed, frame_id=frame.frame_id)
                # Run tracking if enabled, only on new detections
                if self._tracker is not None:
                    self._last_detections = self._tracker.update(self._last_detections)
                # Run event engine on tracked detections
                self._last_events = self._event_engine.update(self._last_detections)

                # Run ANPR Engine
                anpr_events = self._anpr_engine.update(frame.data, self._last_detections)
                self._last_events.extend(anpr_events)

                # --- Face Recognition ---
                if self._face_recognition_enabled and self._face_engine and self._face_detector:
                    current_track_ids: set[int] = set()
                    for det in self._last_detections:
                        if det.class_name != "person" or det.track_id is None:
                            continue
                        tid = det.track_id
                        current_track_ids.add(tid)

                        # Crop the person bounding box
                        x1, y1 = max(0, int(det.bbox.x1)), max(0, int(det.bbox.y1))
                        x2 = min(frame.data.shape[1] - 1, int(det.bbox.x2))
                        y2 = min(frame.data.shape[0] - 1, int(det.bbox.y2))
                        person_crop = frame.data[y1:y2, x1:x2]
                        if person_crop.size == 0:
                            continue

                        # Run face detection on the person crop
                        face_dets = self._face_detector.detect(
                            person_crop, frame_id=frame.frame_id, timestamp=frame.timestamp
                        )
                        if not face_dets:
                            continue

                        # Use the highest-confidence face detection, crop it
                        best_fd = max(face_dets, key=lambda fd: fd.confidence)
                        fx1 = max(0, int(best_fd.bbox.x1))
                        fy1 = max(0, int(best_fd.bbox.y1))
                        fx2 = min(person_crop.shape[1] - 1, int(best_fd.bbox.x2))
                        fy2 = min(person_crop.shape[0] - 1, int(best_fd.bbox.y2))
                        face_crop = person_crop[fy1:fy2, fx1:fx2]
                        if face_crop.size == 0:
                            continue

                        # Identify the face
                        identity = self._face_engine.identify(face_crop, track_id=tid)
                        self._recognized_tracks[tid] = identity

                        # INTRUDER detected → emit immediate critical event
                        if (
                            identity.role == "INTRUDER"
                            and tid not in self._alerted_intruder_tracks
                            and self._transmitter
                        ):
                            self._alerted_intruder_tracks.add(tid)
                            intruder_ev = {
                                "event_type": "FACE_IDENTIFIED_INTRUDER",
                                "severity": "CRITICAL",
                                "track_id": tid,
                                "camera_name": self._source.name,
                                "timestamp": frame.timestamp,
                                "frame_id": frame.frame_id,
                                "class_name": "person",
                                "confidence": identity.confidence,
                                "rule_name": "face:intruder_match",
                                "details": {
                                    "face_id": identity.id,
                                    "name": identity.name,
                                    "match_distance": identity.match_distance,
                                },
                            }
                            self._transmitter.emit_event(intruder_ev)
                            logger.warning(
                                "INTRUDER IDENTIFIED: %s (track #%d, dist=%.3f)",
                                identity.name, tid, identity.match_distance,
                            )

                    # Invalidate cache for tracks that have disappeared
                    for vanished_tid in list(self._recognized_tracks.keys()):
                        if vanished_tid not in current_track_ids:
                            self._recognized_tracks.pop(vanished_tid, None)
                            self._face_engine.invalidate_track(vanished_tid)

                # --- Suppress events for recognized SOLDIER tracks ---
                soldier_track_ids = {
                    tid
                    for tid, ident in self._recognized_tracks.items()
                    if ident.role == "SOLDIER"
                }
                if soldier_track_ids:
                    original_count = len(self._last_events)
                    self._last_events = [
                        ev for ev in self._last_events
                        if ev.track_id not in soldier_track_ids
                    ]
                    suppressed = original_count - len(self._last_events)
                    if suppressed:
                        logger.debug("Suppressed %d events for recognized soldier tracks", suppressed)

                # Transmit events to Command Center Backend
                if self._transmitter and self._last_events:
                    for ev in self._last_events:
                        ev_dict = {
                            "event_type": str(
                                ev.event_type.name
                                if hasattr(ev.event_type, "name")
                                else ev.event_type
                            ),
                            "severity": str(
                                ev.severity.name if hasattr(ev.severity, "name") else ev.severity
                            ),
                            "track_id": ev.track_id,
                            "camera_name": ev.camera_name,
                            "timestamp": ev.timestamp,
                            "frame_id": ev.frame_id,
                            "class_name": ev.class_name,
                            "confidence": ev.confidence,
                            "rule_name": ev.rule_name,
                            "details": ev.details,
                        }
                        self._transmitter.emit_event(ev_dict)

                # Run incident engine
                new_incidents = self._incident_generator.update(self._last_events)
                if new_incidents:
                    # Keep track of active incidents, trim if too many
                    self._active_incidents.extend(new_incidents)
                    if len(self._active_incidents) > 5:
                        self._active_incidents = self._active_incidents[-5:]

                    if self._transmitter:
                        for inc in new_incidents:
                            inc_dict = {
                                "incident_id": inc.incident_id,
                                "incident_type": str(
                                    getattr(inc, "incident_type", "BORDER_SECURITY_ALERT")
                                ),
                                "severity": str(
                                    inc.severity.name
                                    if hasattr(inc.severity, "name")
                                    else inc.severity
                                ),
                                "risk_score": getattr(inc, "risk_score", 0.0),
                                "summary": inc.summary,
                                "description": getattr(inc, "description", inc.summary),
                                "camera_name": getattr(inc, "camera_name", self._source.name),
                                "camera_id": getattr(inc, "camera_name", self._source.name),
                                "track_id": getattr(inc, "track_id", None),
                                "status": "OPEN",
                                "timestamp": getattr(inc, "timestamp", time.time()),
                                "triggering_events": [
                                    {
                                        "event_type": str(
                                            ev.event_type.name
                                            if hasattr(ev.event_type, "name")
                                            else ev.event_type
                                        ),
                                        "severity": str(
                                            ev.severity.name
                                            if hasattr(ev.severity, "name")
                                            else ev.severity
                                        ),
                                        "rule_name": getattr(ev, "rule_name", ""),
                                        "track_id": getattr(ev, "track_id", None),
                                        "timestamp": getattr(ev, "timestamp", None),
                                    }
                                    for ev in getattr(inc, "triggering_events", []) or []
                                ],
                            }
                            self._transmitter.emit_incident(inc_dict)

                # Cleanup stale tracks from incident engine
                active_tids = {d.track_id for d in self._last_detections if d.track_id is not None}
                self._incident_generator.cleanup_stale_tracks(active_tids)

            t_inf_end = time.perf_counter()
            inference_latency_ms = (t_inf_end - t_inf_start) * 1000.0

            # --- Annotation ---
            annotated = self._annotate(frame.data, self._last_detections)
            # Draw event zones/lines overlay
            self._event_engine.draw(annotated)

            if self._active_incidents:
                # If we have incidents, show them prominently instead of raw events
                self._draw_incidents(annotated, self._active_incidents)
            else:
                # Otherwise show raw events
                self._draw_events(annotated, self._last_events)

            # --- End-to-end latency ---
            e2e_ms = (time.perf_counter() - (t_inf_start - (capture_ts - time.time()))) * 1000.0
            e2e_ms = max(e2e_ms, inference_latency_ms)  # floor at inference time

            # --- Metrics ---
            m = self._metrics.record(
                frame_id=frame.frame_id,
                capture_ts=capture_ts,
                inference_latency_ms=inference_latency_ms,
                end_to_end_latency_ms=e2e_ms,
                queue_depth=self._source._queue.qsize(),
                dropped_frames=self._source.frames_dropped,
                num_detections=len(self._last_detections),
            )

            if self._loop_frame_count % self._metrics_print_every_n == 0:
                self._metrics.print_summary(m)
                if self._transmitter:
                    ram_pct = (m.ram_used_mb / m.ram_total_mb * 100) if m.ram_total_mb else 0.0
                    self._transmitter.emit_metrics(
                        {
                            "camera_name": self._source.name,
                            "fps": m.fps_rolling,
                            "inference_latency_ms": m.inference_latency_ms,
                            "end_to_end_latency_ms": m.end_to_end_latency_ms,
                            "num_detections": m.num_detections,
                            "dropped_frames": m.dropped_frames,
                            "cpu_percent": m.cpu_percent,
                            "ram_percent": ram_pct,
                            "ram_used_mb": m.ram_used_mb,
                            "gpu_utilization": m.gpu_utilization_pct or 0.0,
                            "gpu_memory_used_mb": m.vram_used_mb or 0.0,
                            "gpu_temperature_c": m.gpu_temp_celsius or 0.0,
                            "active_cameras": 1,
                        }
                    )
                    self._transmitter.emit_heartbeat(
                        camera_id=self._source.name,
                        status="ONLINE",
                        fps=m.fps_rolling,
                        stream_url=self._advertised_stream_url(),
                    )

            # --- Display / Streaming ---
            if self._streamer:
                # The MJPEG Streamer is now fed directly by VideoSource in the background thread
                # to ensure smooth, raw video feed without AI processing lag.
                pass

            if self._display:
                self._show(annotated, m)

            # --- Save ---
            if self._save_annotated and self._output_video_path:
                self._write_frame(annotated)

        logger.info("EdgeProcessor loop ended  total_frames=%d", self._loop_frame_count)

    # ------------------------------------------------------------------
    # Annotation
    # ------------------------------------------------------------------

    def _annotate(self, frame: np.ndarray, detections: List[Detection]) -> np.ndarray:
        """
        Draw bounding boxes and labels on a copy of the frame.

        Args:
            frame:      Original BGR frame (not the preprocessed one — we
                        annotate at original resolution for display quality).
            detections: List of Detection objects to draw.

        Returns:
            Annotated BGR frame (copy of input).
        """
        out = frame.copy()
        h, w = out.shape[:2]

        for det in detections:
            colour = _CLASS_COLOURS.get(det.class_name, _DEFAULT_COLOUR)

            x1 = int(det.bbox.x1)
            y1 = int(det.bbox.y1)
            x2 = int(det.bbox.x2)
            y2 = int(det.bbox.y2)

            # Clamp to frame bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w - 1, x2), min(h - 1, y2)

            # Bounding box
            cv2.rectangle(out, (x1, y1), (x2, y2), colour, thickness=2)

            # Label: "person 0.87" or "car #23 0.91" (track_id in Phase 2)
            label = f"{det.class_name} {det.confidence:.2f}"
            if det.track_id is not None:
                label = f"#{det.track_id} {label}"

            # Label background
            (lw, lh), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            label_y1 = max(y1 - lh - baseline - 4, 0)
            cv2.rectangle(
                out,
                (x1, label_y1),
                (x1 + lw + 2, y1),
                colour,
                thickness=cv2.FILLED,
            )

            # Label text
            cv2.putText(
                out,
                label,
                (x1 + 1, y1 - baseline - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 0, 0),  # Black text
                thickness=1,
                lineType=cv2.LINE_AA,
            )

            # --- Face Identity Overlay ---
            if det.class_name == "person" and det.track_id is not None:
                identity = self._recognized_tracks.get(det.track_id)
                if identity and identity.role != "UNKNOWN":
                    if identity.role == "SOLDIER":
                        id_colour = (0, 220, 80)   # BGR: bright green
                        id_label = f"[SOLDIER] {identity.name[:16]}"
                    else:  # INTRUDER
                        id_colour = (0, 0, 220)    # BGR: red
                        id_label = f"[INTRUDER] {identity.name[:14]}"

                    (ilw, ilh), ibl = cv2.getTextSize(id_label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    # Draw below the bbox
                    iy1 = y2 + 1
                    iy2 = y2 + ilh + ibl + 4
                    cv2.rectangle(out, (x1, iy1), (x1 + ilw + 4, iy2), id_colour, cv2.FILLED)
                    cv2.putText(
                        out,
                        id_label,
                        (x1 + 2, iy2 - ibl - 1),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 0),
                        thickness=1,
                        lineType=cv2.LINE_AA,
                    )

        # HUD: FPS + detections count (top-left corner)
        return out

    def _draw_incidents(self, frame: np.ndarray, incidents: List[Incident]) -> None:
        """
        Draw active incidents as a high-visibility banner.
        """
        if not incidents:
            return

        h, w = frame.shape[:2]
        _SEVERITY_COLOURS = {
            "low": (180, 180, 180),
            "medium": (0, 165, 255),
            "high": (0, 0, 255),
            "critical": (0, 0, 255),  # Flashing handled below
        }

        y = h - 10
        # Draw up to 3 most recent incidents from bottom up
        for inc in reversed(incidents[-3:]):
            colour = _SEVERITY_COLOURS.get(inc.severity.value, (200, 200, 200))

            # Make critical incidents flash
            if inc.severity.value == "critical":
                # Flash every ~0.25 seconds
                if int(time.time() * 4) % 2 == 0:
                    colour = (255, 255, 255)  # Flash white

            text = f"!!! INCIDENT: {inc.description} [Track #{inc.track_id}] !!!"
            (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)

            # Red background for the text
            cv2.rectangle(
                frame, (8, y - th - baseline - 4), (tw + 16, y + 4), (0, 0, 150), cv2.FILLED
            )
            cv2.rectangle(frame, (8, y - th - baseline - 4), (tw + 16, y + 4), colour, 2)
            cv2.putText(
                frame,
                text,
                (12, y - baseline),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                colour,
                2,
                cv2.LINE_AA,
            )
            y -= th + baseline + 12

    def _draw_events(self, frame: np.ndarray, events: "List[SurveillanceEvent]") -> None:
        """
        Draw active event alerts as a scrolling banner at the bottom of the frame.
        Each event is shown as a coloured pill with the event type and track ID.
        """
        if not events:
            return

        for ev in events:
            if ev.event_type == EventType.VEHICLE_ANPR:
                # Draw plate text above the vehicle bounding box
                plate_text = ev.details.get("plate", "UNKNOWN")
                x, y = int(ev.location[0]), int(ev.location[1]) - 40

                (tw, th), baseline = cv2.getTextSize(plate_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(
                    frame, (x, y - th - baseline - 4), (x + tw + 16, y + 4), (0, 0, 0), cv2.FILLED
                )
                cv2.rectangle(
                    frame, (x, y - th - baseline - 4), (x + tw + 16, y + 4), (0, 255, 0), 2
                )
                cv2.putText(
                    frame,
                    plate_text,
                    (x + 8, y - baseline),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )
            elif ev.rule_name.startswith("zone:"):
                pass

        h, w = frame.shape[:2]
        _SEVERITY_COLOURS = {
            "low": (180, 180, 180),
            "medium": (0, 165, 255),  # Orange
            "high": (0, 0, 255),  # Red
            "critical": (0, 0, 200),  # Dark red + flash
        }

        y = h - 10
        # Draw up to 5 most recent events from bottom up
        for ev in reversed(events[-5:]):
            colour = _SEVERITY_COLOURS.get(ev.severity.value, (200, 200, 200))
            text = f"! {ev.event_type.name.replace('_', ' ')} | #{ev.track_id} | {ev.rule_name}"
            (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            # Background pill
            cv2.rectangle(
                frame, (8, y - th - baseline - 2), (tw + 16, y + 2), (20, 20, 20), cv2.FILLED
            )
            cv2.rectangle(frame, (8, y - th - baseline - 2), (tw + 16, y + 2), colour, 1)
            cv2.putText(
                frame,
                text,
                (12, y - baseline),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                colour,
                1,
                cv2.LINE_AA,
            )
            y -= th + baseline + 8

    def _draw_hud(self, frame: np.ndarray, fps: float, num_det: int, dropped: int) -> None:
        """Draw a semi-transparent HUD overlay on the frame (in-place)."""
        num_events = len(self._last_events)
        num_incidents = len(self._active_incidents)
        hud_lines = [
            f"FPS: {fps:.1f}",
            f"Det: {num_det}",
            f"Events: {num_events}",
            f"Incidents: {num_incidents}",
            f"Drop: {dropped}",
            f"Cam: {self._source.name}",
        ]
        y = 24
        for line in hud_lines:
            cv2.putText(
                frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA
            )
            y += 22

    def _show(self, frame: np.ndarray, m) -> None:
        """Display annotated frame in an OpenCV window."""
        self._draw_hud(frame, m.fps_rolling, m.num_detections, m.dropped_frames)
        cv2.imshow(self._window_name, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:  # 'q' or Escape
            logger.info("User pressed quit key — stopping.")
            self._running = False

    def _write_frame(self, frame: np.ndarray) -> None:
        """Write an annotated frame to the output video file."""
        if self._video_writer is None:
            h, w = frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self._video_writer = cv2.VideoWriter(self._output_video_path, fourcc, 20.0, (w, h))
            logger.info("VideoWriter opened: %s (%dx%d)", self._output_video_path, w, h)
        self._video_writer.write(frame)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def _shutdown(self) -> None:
        """Release all resources cleanly."""
        self._running = False
        self._metrics.close()

        if self._video_writer:
            self._video_writer.release()
            logger.info("VideoWriter closed.")

        if self._display:
            cv2.destroyAllWindows()

        if self._streamer:
            self._streamer.stop()

        if self._transmitter:
            self._transmitter.stop()

        if self._face_engine:
            self._face_engine.stop()

        logger.info("EdgeProcessor shut down cleanly.")

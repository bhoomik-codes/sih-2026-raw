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
import time
from typing import List, Optional

import cv2
import numpy as np

from apps.edge.metrics import MetricsCollector
from apps.edge.video_source import Frame, VideoSource
from cv.detection.base import Detection, DetectorBase
from cv.preprocessing.frame_prep import build_preprocessing_pipeline
from cv.tracking.byte_tracker import ByteTracker
from intelligence.events.engine import EventEngine
from intelligence.events.base import SurveillanceEvent, EventType
from intelligence.incidents.generator import IncidentGenerator
from intelligence.incidents.base import Incident
from intelligence.anpr.engine import ANPREngine

logger = logging.getLogger(__name__)

# Annotation colours per class — BGR format
_CLASS_COLOURS: dict[str, tuple[int, int, int]] = {
    "person":     (0, 255, 0),      # Green
    "car":        (255, 165, 0),    # Orange
    "motorcycle": (255, 0, 255),    # Magenta
    "bus":        (0, 165, 255),    # Orange-ish
    "truck":      (0, 0, 255),      # Red
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
        tracker_type = config.get("tracker", {}).get("type", None)
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

        # --- Processor settings ---
        proc = config.get("processor", config.get("output", {}))
        self._inference_every_n: int = int(
            config.get("detector", {}).get("inference_every_n_frames", 3)
        )
        self._display: bool = bool(proc.get("display", True))
        self._save_annotated: bool = bool(proc.get("save_annotated", False))
        self._output_video_path: Optional[str] = proc.get("output_video_path", None)
        self._metrics_print_every_n: int = int(proc.get("metrics_print_every_n", 30))
        self._window_name: str = f"IBVAP – {self._source.name}"

        # --- Preprocessing pipeline ---
        self._preprocess = build_preprocessing_pipeline(config)

        # --- Metrics ---
        csv_path = config.get("output", {}).get("metrics_csv", None)
        self._metrics = MetricsCollector(csv_path=csv_path)

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

        try:
            self._loop()
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt — shutting down.")
        finally:
            self._shutdown()

    def stop(self) -> None:
        """Signal the inference loop to stop after the current frame."""
        self._running = False

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
                self._last_detections = self._detector.detect(
                    processed, frame_id=frame.frame_id
                )
                # Run tracking if enabled, only on new detections
                if self._tracker is not None:
                    self._last_detections = self._tracker.update(self._last_detections)
                # Run event engine on tracked detections
                self._last_events = self._event_engine.update(self._last_detections)
                
                # Run ANPR Engine
                anpr_events = self._anpr_engine.update(frame.data, self._last_detections)
                self._last_events.extend(anpr_events)
                
                # Run incident engine
                new_incidents = self._incident_generator.update(self._last_events)
                if new_incidents:
                    # Keep track of active incidents, trim if too many
                    self._active_incidents.extend(new_incidents)
                    if len(self._active_incidents) > 5:
                        self._active_incidents = self._active_incidents[-5:]

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

            # --- Display ---
            if self._display:
                self._show(annotated, m)

            # --- Save ---
            if self._save_annotated and self._output_video_path:
                self._write_frame(annotated)

        logger.info(
            "EdgeProcessor loop ended  total_frames=%d", self._loop_frame_count
        )

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
            (lw, lh), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1
            )
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
            "low":      (180, 180, 180),
            "medium":   (0, 165, 255),
            "high":     (0, 0, 255),
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
                    colour = (255, 255, 255) # Flash white

            text = f"!!! INCIDENT: {inc.description} [Track #{inc.track_id}] !!!"
            (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            
            # Red background for the text
            cv2.rectangle(frame, (8, y - th - baseline - 4), (tw + 16, y + 4), (0, 0, 150), cv2.FILLED)
            cv2.rectangle(frame, (8, y - th - baseline - 4), (tw + 16, y + 4), colour, 2)
            cv2.putText(frame, text, (12, y - baseline), cv2.FONT_HERSHEY_SIMPLEX, 0.7, colour, 2, cv2.LINE_AA)
            y -= th + baseline + 12

    def _draw_events(
        self, frame: np.ndarray, events: "List[SurveillanceEvent]"
    ) -> None:
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
                cv2.rectangle(frame, (x, y - th - baseline - 4), (x + tw + 16, y + 4), (0, 0, 0), cv2.FILLED)
                cv2.rectangle(frame, (x, y - th - baseline - 4), (x + tw + 16, y + 4), (0, 255, 0), 2)
                cv2.putText(frame, plate_text, (x + 8, y - baseline), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
            elif ev.rule_name.startswith("zone:"):
                pass

        h, w = frame.shape[:2]
        _SEVERITY_COLOURS = {
            "low":      (180, 180, 180),
            "medium":   (0, 165, 255),   # Orange
            "high":     (0, 0, 255),     # Red
            "critical": (0, 0, 200),     # Dark red + flash
        }

        y = h - 10
        # Draw up to 5 most recent events from bottom up
        for ev in reversed(events[-5:]):
            colour = _SEVERITY_COLOURS.get(ev.severity.value, (200, 200, 200))
            text = f"! {ev.event_type.name.replace('_', ' ')} | #{ev.track_id} | {ev.rule_name}"
            (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            # Background pill
            cv2.rectangle(frame, (8, y - th - baseline - 2), (tw + 16, y + 2), (20, 20, 20), cv2.FILLED)
            cv2.rectangle(frame, (8, y - th - baseline - 2), (tw + 16, y + 2), colour, 1)
            cv2.putText(frame, text, (12, y - baseline), cv2.FONT_HERSHEY_SIMPLEX, 0.55, colour, 1, cv2.LINE_AA)
            y -= th + baseline + 8

    def _draw_hud(
        self, frame: np.ndarray, fps: float, num_det: int, dropped: int
    ) -> None:
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
                frame, line, (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA
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
            self._video_writer = cv2.VideoWriter(
                self._output_video_path, fourcc, 20.0, (w, h)
            )
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

        logger.info("EdgeProcessor shut down cleanly.")

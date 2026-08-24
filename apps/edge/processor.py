"""
apps.edge.processor
---------------------
EdgeProcessor — the central inference loop for Phase 1.

Pipeline (per frame):
    1. Read frame from VideoSource (latest-frame queue)
    2. Apply preprocessing (ROI mask → resize)
    3. Every N frames: run detector → List[Detection]
    4. Annotate frame with bounding boxes and labels
    5. Display via OpenCV window (optional)
    6. Write annotated frame to output video (optional)
    7. Collect and print metrics (FPS, VRAM, latency, etc.)
    8. Graceful shutdown on KeyboardInterrupt / stop()

Phase 2+:
    Step 3.5 will insert: Tracker → persistent track IDs
    Step 3.6 will insert: Event Engine → zone/fence/loitering checks
    These are not present in Phase 1.
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

            t_inf_end = time.perf_counter()
            inference_latency_ms = (t_inf_end - t_inf_start) * 1000.0

            # --- Annotation ---
            annotated = self._annotate(frame.data, self._last_detections)

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

    def _draw_hud(
        self, frame: np.ndarray, fps: float, num_det: int, dropped: int
    ) -> None:
        """Draw a semi-transparent HUD overlay on the frame (in-place)."""
        hud_lines = [
            f"FPS: {fps:.1f}",
            f"Det: {num_det}",
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

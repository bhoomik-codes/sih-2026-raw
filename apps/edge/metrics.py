"""
apps.edge.metrics
------------------
Real-time performance metrics collection for the edge processing loop.

Tracks per-frame inference latency, rolling FPS, GPU health (VRAM, utilization,
temperature), CPU/RAM usage, and dropped frame counts. Writes to CSV for
offline analysis and benchmark table generation.

Design notes:
- pynvml is used for GPU metrics (NVIDIA Management Library).
  If unavailable (e.g. CPU-only machine), GPU metrics are returned as None.
- All metrics are collected synchronously in the inference loop — no background
  thread needed since pynvml calls are fast (~0.1ms each).
- CSV writing is buffered and flushed every N rows to avoid I/O becoming
  a bottleneck in the inference loop.
"""

from __future__ import annotations

import csv
import logging
import os
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Deque, Optional

logger = logging.getLogger(__name__)

# Number of recent frames to use for rolling FPS calculation
_ROLLING_WINDOW: int = 30

# CSV flush interval (rows before flush to disk)
_CSV_FLUSH_EVERY: int = 100


@dataclass
class FrameMetrics:
    """
    Performance snapshot for a single processed frame.

    All timing values are in milliseconds. GPU values are None if
    pynvml is unavailable or GPU metrics query failed.
    """

    frame_id: int
    wall_time: float  # Unix timestamp (seconds)

    # Inference timing
    inference_latency_ms: float  # Time spent in detector.detect()
    end_to_end_latency_ms: float  # Time from frame capture to annotation complete

    # Throughput
    fps_rolling: float  # Rolling FPS over last _ROLLING_WINDOW frames

    # GPU (None if unavailable)
    gpu_utilization_pct: Optional[float]
    vram_used_mb: Optional[float]
    vram_total_mb: Optional[float]
    gpu_temp_celsius: Optional[float]
    gpu_clock_mhz: Optional[float]

    # CPU / RAM
    cpu_percent: float
    ram_used_mb: float
    ram_total_mb: float

    # Queue / pipeline health
    queue_depth: int
    dropped_frames: int

    # Detections
    num_detections: int


class MetricsCollector:
    """
    Collects, aggregates, and persists per-frame performance metrics.

    Args:
        csv_path:    Output CSV file path. None = no CSV output.
        gpu_index:   NVIDIA GPU index to monitor (default: 0).
    """

    def __init__(
        self,
        csv_path: Optional[str] = None,
        gpu_index: int = 0,
    ) -> None:
        self._csv_path = csv_path
        self._gpu_index = gpu_index

        # Rolling FPS state
        self._frame_times: Deque[float] = deque(maxlen=_ROLLING_WINDOW)

        # CSV state
        self._csv_file = None
        self._csv_writer = None
        self._rows_since_flush: int = 0

        # pynvml handle
        self._nvml_handle = None
        self._nvml_available: bool = False
        self._init_nvml()

        # psutil for CPU/RAM
        self._psutil_available: bool = False
        self._init_psutil()

        # Open CSV if requested
        if self._csv_path:
            self._open_csv()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(
        self,
        frame_id: int,
        capture_ts: float,
        inference_latency_ms: float,
        end_to_end_latency_ms: float,
        queue_depth: int,
        dropped_frames: int,
        num_detections: int,
    ) -> FrameMetrics:
        """
        Record metrics for one processed frame and return the snapshot.

        Args:
            frame_id:               Frame counter.
            capture_ts:             Unix timestamp when the frame was captured.
            inference_latency_ms:   Time spent inside detector.detect().
            end_to_end_latency_ms:  Total processing time from capture to display.
            queue_depth:            Current video source queue depth.
            dropped_frames:         Total frames dropped by video source so far.
            num_detections:         Number of Detection objects returned.

        Returns:
            FrameMetrics snapshot.
        """
        now = time.time()
        self._frame_times.append(now)

        fps = self._compute_fps()
        gpu_util, vram_used, vram_total, gpu_temp, gpu_clock = self._query_gpu()
        cpu_pct, ram_used, ram_total = self._query_cpu_ram()

        m = FrameMetrics(
            frame_id=frame_id,
            wall_time=now,
            inference_latency_ms=inference_latency_ms,
            end_to_end_latency_ms=end_to_end_latency_ms,
            fps_rolling=fps,
            gpu_utilization_pct=gpu_util,
            vram_used_mb=vram_used,
            vram_total_mb=vram_total,
            gpu_temp_celsius=gpu_temp,
            gpu_clock_mhz=gpu_clock,
            cpu_percent=cpu_pct,
            ram_used_mb=ram_used,
            ram_total_mb=ram_total,
            queue_depth=queue_depth,
            dropped_frames=dropped_frames,
            num_detections=num_detections,
        )

        if self._csv_writer:
            self._write_row(m)

        return m

    def print_summary(self, metrics: FrameMetrics) -> None:
        """Print a one-line summary to stdout (for console monitoring)."""
        gpu_str = (
            f"GPU={metrics.gpu_utilization_pct:.0f}% "
            f"VRAM={metrics.vram_used_mb:.0f}/{metrics.vram_total_mb:.0f}MB "
            f"Temp={metrics.gpu_temp_celsius:.0f}°C"
            if metrics.gpu_utilization_pct is not None
            else "GPU=N/A"
        )
        print(
            f"[Frame {metrics.frame_id:>6}] "
            f"FPS={metrics.fps_rolling:5.1f} "
            f"Inf={metrics.inference_latency_ms:6.1f}ms "
            f"E2E={metrics.end_to_end_latency_ms:6.1f}ms "
            f"Det={metrics.num_detections:>2} "
            f"Q={metrics.queue_depth} "
            f"Drop={metrics.dropped_frames} "
            f"CPU={metrics.cpu_percent:.0f}% "
            f"{gpu_str}",
            flush=True,
        )

    def close(self) -> None:
        """Flush and close CSV file. Shut down pynvml."""
        if self._csv_file:
            self._csv_file.flush()
            self._csv_file.close()
            self._csv_file = None
            logger.info("Metrics CSV closed: %s", self._csv_path)

        if self._nvml_available:
            try:
                import pynvml

                pynvml.nvmlShutdown()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_fps(self) -> float:
        """Rolling FPS over the last _ROLLING_WINDOW frame timestamps."""
        if len(self._frame_times) < 2:
            return 0.0
        elapsed = self._frame_times[-1] - self._frame_times[0]
        if elapsed <= 0:
            return 0.0
        return (len(self._frame_times) - 1) / elapsed

    def _init_nvml(self) -> None:
        """Attempt to initialise pynvml. Silently degrade if unavailable."""
        try:
            import pynvml

            pynvml.nvmlInit()
            self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(self._gpu_index)
            self._nvml_available = True
            device_name = pynvml.nvmlDeviceGetName(self._nvml_handle)
            logger.info("pynvml initialised: GPU %d — %s", self._gpu_index, device_name)
        except Exception as exc:
            logger.warning("pynvml unavailable — GPU metrics disabled (%s)", exc)
            self._nvml_available = False

    def _init_psutil(self) -> None:
        try:
            import psutil  # noqa: F401

            self._psutil_available = True
        except ImportError:
            logger.warning("psutil unavailable — CPU/RAM metrics disabled")

    def _query_gpu(
        self,
    ) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
        """Query GPU utilization, VRAM, temp, and clock. Returns None on failure."""
        if not self._nvml_available:
            return None, None, None, None, None
        try:
            import pynvml

            util = pynvml.nvmlDeviceGetUtilizationRates(self._nvml_handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
            temp = pynvml.nvmlDeviceGetTemperature(self._nvml_handle, pynvml.NVML_TEMPERATURE_GPU)
            clock = pynvml.nvmlDeviceGetClockInfo(self._nvml_handle, pynvml.NVML_CLOCK_SM)
            return (
                float(util.gpu),
                float(mem.used) / (1024**2),
                float(mem.total) / (1024**2),
                float(temp),
                float(clock),
            )
        except Exception as exc:
            logger.debug("GPU metrics query failed: %s", exc)
            return None, None, None, None, None

    def _query_cpu_ram(self) -> tuple[float, float, float]:
        """Query CPU% and RAM usage. Returns zeros if psutil unavailable."""
        if not self._psutil_available:
            return 0.0, 0.0, 0.0
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            return cpu, float(ram.used) / (1024**2), float(ram.total) / (1024**2)
        except Exception:
            return 0.0, 0.0, 0.0

    def _open_csv(self) -> None:
        """Open CSV file and write header row."""
        os.makedirs(os.path.dirname(self._csv_path) or ".", exist_ok=True)
        self._csv_file = open(self._csv_path, "w", newline="", encoding="utf-8")
        fieldnames = list(
            asdict(
                FrameMetrics(
                    frame_id=0,
                    wall_time=0,
                    inference_latency_ms=0,
                    end_to_end_latency_ms=0,
                    fps_rolling=0,
                    gpu_utilization_pct=None,
                    vram_used_mb=None,
                    vram_total_mb=None,
                    gpu_temp_celsius=None,
                    gpu_clock_mhz=None,
                    cpu_percent=0,
                    ram_used_mb=0,
                    ram_total_mb=0,
                    queue_depth=0,
                    dropped_frames=0,
                    num_detections=0,
                )
            ).keys()
        )
        self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=fieldnames)
        self._csv_writer.writeheader()
        logger.info("Metrics CSV opened: %s", self._csv_path)

    def _write_row(self, m: FrameMetrics) -> None:
        """Write one row to the CSV and flush periodically."""
        self._csv_writer.writerow(asdict(m))
        self._rows_since_flush += 1
        if self._rows_since_flush >= _CSV_FLUSH_EVERY:
            self._csv_file.flush()
            self._rows_since_flush = 0

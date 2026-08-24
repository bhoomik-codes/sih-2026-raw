"""
benchmarks/phase1_benchmark.py
-------------------------------
Phase 1 hardware benchmark: sweeps detector models × resolutions and
measures FPS, inference latency, VRAM, GPU utilization, and temperature.

Run:
    python benchmarks/phase1_benchmark.py
    python benchmarks/phase1_benchmark.py --model yolov8s.pt --frames 1000
    python benchmarks/phase1_benchmark.py --duration 3600  # 1-hour soak test

Output:
    - Markdown benchmark table printed to stdout
    - CSV written to benchmarks/phase1_results.csv

Design rules:
- No display overhead during benchmark — pure inference timing.
- GPU warmup (50 frames) discarded before recording.
- Runs each (model × resolution) configuration in isolation.
- Reports both short-run and optionally long-duration (thermal) results.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("ibvap.benchmark")

# ── Benchmark configurations ──────────────────────────────────────────────────

# Resolutions to test (width, height) — from context §17 Phase 1
RESOLUTIONS: list[tuple[int, int]] = [
    (640, 360),
    (640, 480),
    (640, 640),
    (960, 540),
    (1280, 720),
]

WARMUP_FRAMES: int = 50
DEFAULT_BENCHMARK_FRAMES: int = 500


# ── Result dataclass ──────────────────────────────────────────────────────────


@dataclass
class BenchmarkResult:
    model: str
    resolution: str
    backend: str
    frames_measured: int
    fps_avg: float
    fps_min: float
    fps_max: float
    latency_avg_ms: float
    latency_p95_ms: float
    vram_peak_mb: Optional[float]
    gpu_util_avg: Optional[float]
    gpu_temp_peak: Optional[float]
    cpu_avg_pct: float
    ram_used_mb: float


# ── GPU / System helpers ──────────────────────────────────────────────────────


def _init_nvml():
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        print(f"[GPU] {name}")
        return pynvml, handle
    except Exception as e:
        print(f"[WARN] pynvml unavailable — GPU metrics disabled ({e})")
        return None, None


def _query_gpu(pynvml, handle):
    if not pynvml or not handle:
        return None, None, None
    try:
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        return float(util.gpu), float(mem.used) / (1024 ** 2), float(temp)
    except Exception:
        return None, None, None


def _query_cpu_ram():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        return cpu, float(ram.used) / (1024 ** 2)
    except Exception:
        return 0.0, 0.0


# ── Benchmark runner ──────────────────────────────────────────────────────────


def run_benchmark(
    model_path: str,
    resolution: tuple[int, int],
    device: str,
    num_frames: int,
    duration_s: Optional[float],
    pynvml,
    nvml_handle,
) -> BenchmarkResult:
    """
    Run one benchmark configuration: model × resolution.

    Returns a BenchmarkResult with aggregated statistics.
    """
    from cv.detection.yolo_detector import YOLODetector

    w, h = resolution
    res_str = f"{w}×{h}"
    model_name = Path(model_path).stem

    print(f"\n{'─'*60}")
    print(f"  Model: {model_name}  Resolution: {res_str}  Device: {device}")
    print(f"{'─'*60}")

    config = {
        "detector": {
            "model": model_path,
            "device": device,
            "conf_threshold": 0.40,
            "iou_threshold": 0.45,
            "imgsz": max(w, h),
            "half": False,
            "verbose": False,
        }
    }

    detector = YOLODetector(config=config)
    detector.load()

    # Create a synthetic BGR frame at the target resolution
    dummy_frame = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)

    # Warmup
    print(f"  Warmup ({WARMUP_FRAMES} frames)...", end=" ", flush=True)
    for _ in range(WARMUP_FRAMES):
        detector.detect(dummy_frame, frame_id=-1)
    print("done")

    # Benchmark
    latencies: list[float] = []
    vram_peaks: list[float] = []
    gpu_utils: list[float] = []
    gpu_temps: list[float] = []
    cpu_pcts: list[float] = []
    ram_mbs: list[float] = []

    max_frames = num_frames
    if duration_s:
        max_frames = 999_999  # unlimited — stop by time

    start_wall = time.perf_counter()
    frame_id = 0

    print(f"  Measuring {max_frames if not duration_s else f'{duration_s}s'} ...", end=" ", flush=True)

    while frame_id < max_frames:
        if duration_s and (time.perf_counter() - start_wall) >= duration_s:
            break

        t0 = time.perf_counter()
        detector.detect(dummy_frame, frame_id=frame_id)
        t1 = time.perf_counter()

        lat_ms = (t1 - t0) * 1000.0
        latencies.append(lat_ms)

        gpu_util, vram_used, gpu_temp = _query_gpu(pynvml, nvml_handle)
        if vram_used is not None:
            vram_peaks.append(vram_used)
        if gpu_util is not None:
            gpu_utils.append(gpu_util)
        if gpu_temp is not None:
            gpu_temps.append(gpu_temp)

        cpu, ram = _query_cpu_ram()
        cpu_pcts.append(cpu)
        ram_mbs.append(ram)

        frame_id += 1

    elapsed = time.perf_counter() - start_wall
    print(f"done ({frame_id} frames in {elapsed:.1f}s)")

    # --- Aggregate ---
    fps_avg = frame_id / elapsed if elapsed > 0 else 0.0
    latencies.sort()
    n = len(latencies)

    result = BenchmarkResult(
        model=model_name,
        resolution=res_str,
        backend="PyTorch FP32",
        frames_measured=frame_id,
        fps_avg=fps_avg,
        fps_min=1000.0 / latencies[-1] if latencies else 0.0,
        fps_max=1000.0 / latencies[0] if latencies else 0.0,
        latency_avg_ms=sum(latencies) / n if n else 0.0,
        latency_p95_ms=latencies[int(n * 0.95)] if n else 0.0,
        vram_peak_mb=max(vram_peaks) if vram_peaks else None,
        gpu_util_avg=sum(gpu_utils) / len(gpu_utils) if gpu_utils else None,
        gpu_temp_peak=max(gpu_temps) if gpu_temps else None,
        cpu_avg_pct=sum(cpu_pcts) / len(cpu_pcts) if cpu_pcts else 0.0,
        ram_used_mb=sum(ram_mbs) / len(ram_mbs) if ram_mbs else 0.0,
    )

    # Cleanup
    del detector
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass

    return result


# ── Output formatting ─────────────────────────────────────────────────────────


def print_table(results: List[BenchmarkResult]) -> None:
    """Print a markdown-formatted benchmark table."""
    print("\n\n## Phase 1 Benchmark Results\n")
    header = (
        "| Model | Resolution | Backend | FPS | Lat(ms) | Lat P95 | "
        "VRAM(MB) | GPU% | Temp°C | CPU% |"
    )
    sep = "|" + "|".join(["---" for _ in range(10)]) + "|"
    print(header)
    print(sep)
    for r in results:
        vram = f"{r.vram_peak_mb:.0f}" if r.vram_peak_mb else "N/A"
        gpu = f"{r.gpu_util_avg:.0f}" if r.gpu_util_avg else "N/A"
        temp = f"{r.gpu_temp_peak:.0f}" if r.gpu_temp_peak else "N/A"
        print(
            f"| {r.model} | {r.resolution} | {r.backend} "
            f"| {r.fps_avg:.1f} | {r.latency_avg_ms:.1f} | {r.latency_p95_ms:.1f} "
            f"| {vram} | {gpu} | {temp} | {r.cpu_avg_pct:.0f} |"
        )
    print()


def save_csv(results: List[BenchmarkResult], path: str) -> None:
    """Save results to a CSV file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fields = [
        "model", "resolution", "backend", "frames_measured",
        "fps_avg", "fps_min", "fps_max",
        "latency_avg_ms", "latency_p95_ms",
        "vram_peak_mb", "gpu_util_avg", "gpu_temp_peak",
        "cpu_avg_pct", "ram_used_mb",
    ]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({k: getattr(r, k) for k in fields})
    print(f"Results saved to: {path}")


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    logging.basicConfig(level=logging.WARNING)

    parser = argparse.ArgumentParser(
        description="IBVAP Phase 1 Hardware Benchmark",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model", nargs="+",
        default=["yolov8n.pt"],
        help="Model weight files to benchmark (space-separated).",
    )
    parser.add_argument(
        "--resolutions", nargs="+",
        default=[f"{w}x{h}" for w, h in RESOLUTIONS],
        help="Resolutions to test as WxH (e.g. 640x640 1280x720).",
    )
    parser.add_argument(
        "--device", default="cuda:0",
        help="PyTorch device string.",
    )
    parser.add_argument(
        "--frames", type=int, default=DEFAULT_BENCHMARK_FRAMES,
        help="Number of frames per configuration (ignored if --duration set).",
    )
    parser.add_argument(
        "--duration", type=float, default=None,
        help="Benchmark duration in seconds per config (thermal soak test).",
    )
    parser.add_argument(
        "--output-csv", default="benchmarks/phase1_results.csv",
        help="Path for output CSV.",
    )
    args = parser.parse_args()

    # Parse resolutions
    resolutions: list[tuple[int, int]] = []
    for res_str in args.resolutions:
        try:
            w, h = map(int, res_str.lower().split("x"))
            resolutions.append((w, h))
        except ValueError:
            print(f"[ERROR] Invalid resolution: {res_str}. Use WxH format.", file=sys.stderr)
            sys.exit(1)

    pynvml_mod, nvml_handle = _init_nvml()

    results: List[BenchmarkResult] = []

    for model_path in args.model:
        for resolution in resolutions:
            r = run_benchmark(
                model_path=model_path,
                resolution=resolution,
                device=args.device,
                num_frames=args.frames,
                duration_s=args.duration,
                pynvml=pynvml_mod,
                nvml_handle=nvml_handle,
            )
            results.append(r)

    print_table(results)
    save_csv(results, args.output_csv)

    if pynvml_mod:
        try:
            pynvml_mod.nvmlShutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()

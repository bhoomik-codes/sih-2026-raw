"""
benchmarks/phase8_benchmark.py
--------------------------------
Phase 8 Multi-Camera Benchmark — 1 camera vs 2 cameras concurrently.

Measures the GPU/CPU overhead of running 2 camera pipelines simultaneously
compared to a single camera. Identifies GPU budget per camera and scaling
characteristics.

Usage:
    python benchmarks/phase8_benchmark.py
    python benchmarks/phase8_benchmark.py --cameras 2 --frames 200 --imgsz 640

Output:
    benchmarks/phase8_results.csv — per-camera, per-run metrics
"""

from __future__ import annotations

import argparse
import csv
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("benchmarks.phase8")

OUTPUT_CSV = "benchmarks/phase8_results.csv"
VIDEO_PATH = "data/videos/test_video.mp4"


def _load_frames(video_path: str, n_frames: int, imgsz: int) -> List[np.ndarray]:
    cap = cv2.VideoCapture(video_path)
    frames = []
    while len(frames) < n_frames:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                break
        frames.append(cv2.resize(frame, (imgsz, imgsz)))
    cap.release()
    logger.info("Loaded %d frames at %dx%d.", len(frames), imgsz, imgsz)
    return frames


def _gpu_vram_mb() -> float:
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return info.used / (1024 ** 2)
    except Exception:
        return 0.0


def _cpu_percent() -> float:
    try:
        import psutil
        return psutil.cpu_percent(interval=None)
    except Exception:
        return 0.0


def _run_camera_thread(
    camera_id: str,
    frames: List[np.ndarray],
    detector,
    results: Dict[str, dict],
) -> None:
    """Single camera inference thread."""
    latencies = []
    t_start = time.perf_counter()

    for i, frame in enumerate(frames):
        t0 = time.perf_counter()
        try:
            detector.detect(frame, frame_id=i)
        except Exception as exc:
            logger.warning("[%s] Frame %d error: %s", camera_id, i, exc)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    t_total = time.perf_counter() - t_start
    fps = len(frames) / t_total if t_total > 0 else 0.0
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

    results[camera_id] = {
        "camera_id": camera_id,
        "n_frames": len(frames),
        "fps": round(fps, 2),
        "latency_ms_avg": round(avg_lat, 2),
    }
    logger.info("[%s] Done: FPS=%.1f  lat=%.1f ms", camera_id, fps, avg_lat)


def benchmark_n_cameras(
    n_cameras: int,
    frames: List[np.ndarray],
    config: dict,
) -> List[dict]:
    """
    Run inference on n_cameras concurrently (one thread per camera).

    Returns a list of per-camera result dicts, plus a 'combined' row.
    """
    from cv.detection.yolo_detector import YOLODetector

    logger.info("=" * 60)
    logger.info("Benchmarking %d camera(s)", n_cameras)
    logger.info("=" * 60)

    # Shared detector — YOLO is thread-safe for inference
    detector = YOLODetector(config)
    detector.load()

    # Warmup
    for _ in range(5):
        try:
            detector.detect(frames[0], frame_id=0)
        except Exception:
            break

    vram_before = _gpu_vram_mb()
    t_wall_start = time.perf_counter()

    thread_results: Dict[str, dict] = {}
    threads = []
    for i in range(n_cameras):
        cam_id = f"CAM-{i+1:02d}"
        t = threading.Thread(
            target=_run_camera_thread,
            args=(cam_id, frames, detector, thread_results),
            name=cam_id,
        )
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    t_wall = time.perf_counter() - t_wall_start
    vram_after = _gpu_vram_mb()

    per_camera = list(thread_results.values())
    for r in per_camera:
        r["n_cameras"] = n_cameras
        r["vram_mb"] = round(max(vram_before, vram_after), 1)
        r["wall_time_s"] = round(t_wall, 2)

    return per_camera


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 8 Benchmark: 1 camera vs N cameras.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--cameras", type=int, default=2)
    parser.add_argument("--frames", type=int, default=300)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--video", default=VIDEO_PATH)
    args = parser.parse_args()

    if not Path(args.video).exists():
        logger.error("Video not found: %s", args.video)
        return

    frames = _load_frames(args.video, args.frames, args.imgsz)
    if not frames:
        logger.error("No frames loaded.")
        return

    config = {
        "detector": {
            "model": "models/pytorch/yolov8n.pt",
            "device": "cuda:0",
            "conf_threshold": 0.25,
            "iou_threshold": 0.45,
            "imgsz": args.imgsz,
            "half": False,
            "verbose": False,
        }
    }

    all_results = []

    # Baseline: 1 camera
    all_results.extend(benchmark_n_cameras(1, frames, config))

    # Multi-camera: N cameras
    if args.cameras > 1:
        all_results.extend(benchmark_n_cameras(args.cameras, frames, config))

    # Save
    output = Path(OUTPUT_CSV)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["camera_id", "n_cameras", "n_frames", "fps", "latency_ms_avg", "vram_mb", "wall_time_s"]
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_results)

    logger.info("Results saved: %s", output)

    print("\n" + "=" * 70)
    print(f"{'Camera':<12} {'N-cams':>6} {'FPS':>8} {'Latency(ms)':>12} {'VRAM(MB)':>10}")
    print("-" * 70)
    for r in all_results:
        print(
            f"{r['camera_id']:<12} {r['n_cameras']:>6} {r['fps']:>8.1f} "
            f"{r['latency_ms_avg']:>12.1f} {r['vram_mb']:>10.0f}"
        )
    print("=" * 70)


if __name__ == "__main__":
    main()

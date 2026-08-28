"""
benchmarks/phase7_benchmark.py
--------------------------------
Phase 7 Optimization Benchmark — PyTorch vs ONNX backend comparison.

Runs 500 frames of inference through each configured backend and records
FPS, inference latency, and VRAM usage. Results saved to CSV.

Usage:
    python benchmarks/phase7_benchmark.py
    python benchmarks/phase7_benchmark.py --frames 200 --imgsz 640

Requirements:
    - ONNX model must exist: python scripts/export_onnx.py first
    - Run from the project root directory

Output:
    benchmarks/phase7_results.csv — comparison table
"""

from __future__ import annotations

import argparse
import csv
import logging
import time
from pathlib import Path
from typing import List

import cv2
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("benchmarks.phase7")

OUTPUT_CSV = "benchmarks/phase7_results.csv"
VIDEO_PATH = "data/videos/test_video.mp4"


def _load_frames(video_path: str, n_frames: int, imgsz: int) -> List[np.ndarray]:
    """Load the first n_frames from the test video, resized to imgsz."""
    cap = cv2.VideoCapture(video_path)
    frames = []
    while len(frames) < n_frames:
        ret, frame = cap.read()
        if not ret:
            # Loop the video if needed
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                break
        frame = cv2.resize(frame, (imgsz, imgsz))
        frames.append(frame)
    cap.release()
    logger.info("Loaded %d frames at %dx%d.", len(frames), imgsz, imgsz)
    return frames


def _gpu_vram_mb() -> float:
    """Return current GPU VRAM usage in MB, or 0 if pynvml unavailable."""
    try:
        import pynvml

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return info.used / (1024**2)
    except Exception:
        return 0.0


def benchmark_backend(
    backend_name: str,
    config: dict,
    frames: List[np.ndarray],
) -> dict:
    """
    Benchmark a single detector backend on the provided frames.

    Returns a dict with keys: backend, n_frames, fps, latency_ms_avg, vram_mb.
    """
    logger.info("=" * 60)
    logger.info("Benchmarking: %s", backend_name)
    logger.info("=" * 60)

    if backend_name == "pytorch_fp32":
        from cv.detection.yolo_detector import YOLODetector

        detector = YOLODetector(config)
    elif backend_name == "pytorch_fp16":
        cfg = dict(config)
        cfg["detector"] = dict(config["detector"])
        cfg["detector"]["half"] = True
        from cv.detection.yolo_detector import YOLODetector

        detector = YOLODetector(cfg)
    elif backend_name == "onnx":
        from cv.detection.onnx_detector import ONNXDetector

        detector = ONNXDetector(config)
    else:
        raise ValueError(f"Unknown backend: {backend_name}")

    try:
        detector.load()
    except Exception as exc:
        logger.error("Failed to load detector for %s: %s", backend_name, exc)
        return {
            "backend": backend_name,
            "n_frames": 0,
            "fps": 0.0,
            "latency_ms_avg": 0.0,
            "vram_mb": 0.0,
            "error": str(exc),
        }

    # Warmup
    logger.info("Warming up...")
    for _ in range(10):
        try:
            detector.detect(frames[0], frame_id=0)
        except Exception:
            break

    # Benchmark
    latencies = []
    vram_before = _gpu_vram_mb()
    t_start = time.perf_counter()

    for i, frame in enumerate(frames):
        t0 = time.perf_counter()
        try:
            detector.detect(frame, frame_id=i)
        except Exception as exc:
            logger.warning("Frame %d error: %s", i, exc)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    t_total = time.perf_counter() - t_start
    vram_after = _gpu_vram_mb()

    fps = len(frames) / t_total if t_total > 0 else 0.0
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

    result = {
        "backend": backend_name,
        "n_frames": len(frames),
        "fps": round(fps, 2),
        "latency_ms_avg": round(avg_lat, 2),
        "vram_mb": round(max(vram_before, vram_after), 1),
    }
    logger.info(
        "Result: FPS=%.1f  lat=%.1f ms  VRAM=%.0f MB",
        fps,
        avg_lat,
        result["vram_mb"],
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 7 Benchmark: PyTorch vs ONNX inference backends.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--frames", type=int, default=500, help="Number of frames per backend.")
    parser.add_argument("--imgsz", type=int, default=640, help="Inference resolution.")
    parser.add_argument("--video", default=VIDEO_PATH, help="Test video path.")
    parser.add_argument("--onnx-model", default="models/onnx/yolov8n.onnx", help="ONNX model path.")
    args = parser.parse_args()

    if not Path(args.video).exists():
        logger.error("Video not found: %s — run python scripts/get_test_video.py", args.video)
        return

    frames = _load_frames(args.video, args.frames, args.imgsz)
    if not frames:
        logger.error("Could not load any frames from %s", args.video)
        return

    # Base config for PyTorch backends
    pytorch_config = {
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

    # Config for ONNX backend
    onnx_config = {
        "detector": {
            "model": args.onnx_model,
            "device": "cuda:0",
            "conf_threshold": 0.25,
            "iou_threshold": 0.45,
            "imgsz": args.imgsz,
        }
    }

    results = []

    # 1. PyTorch FP32
    results.append(benchmark_backend("pytorch_fp32", pytorch_config, frames))

    # 2. PyTorch FP16
    results.append(benchmark_backend("pytorch_fp16", pytorch_config, frames))

    # 3. ONNX (only if model exists)
    if Path(args.onnx_model).exists():
        results.append(benchmark_backend("onnx", onnx_config, frames))
    else:
        logger.warning(
            "ONNX model not found at %s. Skipping ONNX benchmark.\n"
            "Run: python scripts/export_onnx.py",
            args.onnx_model,
        )

    # Save results
    output = Path(OUTPUT_CSV)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["backend", "n_frames", "fps", "latency_ms_avg", "vram_mb"]

    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    logger.info("Results saved to: %s", output)

    # Print comparison table
    print("\n" + "=" * 65)
    print(f"{'Backend':<18} {'FPS':>8} {'Latency (ms)':>14} {'VRAM (MB)':>10}")
    print("-" * 65)
    for r in results:
        print(
            f"{r['backend']:<18} {r['fps']:>8.1f} {r['latency_ms_avg']:>14.1f} {r['vram_mb']:>10.0f}"
        )
    print("=" * 65)


if __name__ == "__main__":
    main()

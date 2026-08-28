"""
apps.edge.multi_main
---------------------
Multi-camera CLI entry point for Phase 8.

Reads a list of cameras from YAML config and runs the IBVAP AI pipeline
on all of them concurrently. One EdgeProcessor (detector + tracker + event
engine) is used per camera, each running in its own thread.

Usage:
    python -m apps.edge.multi_main --config configs/phase8_default.yaml
    python -m apps.edge.multi_main --config configs/phase8_default.yaml --no-display

Config structure:
    cameras:
      - id: "BOP-CAM-01"
        source: "data/videos/test_video.mp4"
        name: "Border East"
        pipeline: "opencv"       # or "gstreamer"
      - id: "BOP-CAM-02"
        source: "data/videos/test_video.mp4"
        name: "Border West"
        pipeline: "opencv"

    # All other keys (detector, tracker, event_engine, etc.) are
    # shared across all cameras. Per-camera overrides are not yet supported.
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading
from pathlib import Path
from typing import List

import yaml

logger = logging.getLogger("ibvap.multi_main")


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


def _load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        print(f"[ERROR] Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _run_single_camera(
    camera_cfg: dict,
    shared_config: dict,
    no_display: bool,
    results: dict,
) -> None:
    """
    Thread target: run a single camera pipeline until exhausted or interrupted.

    Args:
        camera_cfg:    Config dict for this specific camera.
        shared_config: Full YAML config (detector, tracker, event_engine, etc.)
        no_display:    If True, disable OpenCV display windows.
        results:       Shared dict to store per-camera outcome metrics.
    """
    camera_id = camera_cfg.get("id", camera_cfg.get("name", "CAM-?"))
    thread_name = threading.current_thread().name
    logger.info("[%s] Camera thread %s starting.", camera_id, thread_name)

    # Build merged config: shared settings + camera-specific source
    config = dict(shared_config)
    config["camera"] = {
        "source": camera_cfg.get("source", 0),
        "name": camera_cfg.get("name", camera_id),
        "max_queue_size": camera_cfg.get("max_queue_size", 2),
        "reconnect_delay_s": camera_cfg.get("reconnect_delay_s", 3.0),
    }
    if no_display:
        config.setdefault("output", {})["display"] = False

    # Override metrics CSV to include camera_id
    metrics_base = shared_config.get("output", {}).get("metrics_csv", "benchmarks/phase8_run.csv")
    base_stem = Path(metrics_base).stem
    base_ext = Path(metrics_base).suffix
    config.setdefault("output", {})["metrics_csv"] = (
        f"{Path(metrics_base).parent}/{base_stem}_{camera_id}{base_ext}"
    )

    from apps.edge.processor import EdgeProcessor
    from cv.detection.yolo_detector import YOLODetector

    # Use pipeline-backed VideoSource
    pipeline_backend = camera_cfg.get("pipeline", "opencv").lower()
    if pipeline_backend == "gstreamer":
        from pipelines.gstreamer.pipeline import GStreamerPipeline

        pipeline = GStreamerPipeline(camera_cfg, camera_id)
    else:
        from pipelines.opencv.pipeline import OpenCVPipeline

        pipeline = OpenCVPipeline(camera_cfg, camera_id)

    # For EdgeProcessor we need a VideoSource-compatible object.
    # OpenCVPipeline wraps VideoSource directly and exposes the same interface.
    # Use the internal _video_source for EdgeProcessor if available (OpenCV),
    # or use a VideoSource directly.
    det_cfg = config.get("detector", {})
    backend = det_cfg.get("backend", "pytorch").lower()
    if backend == "onnx":
        from cv.detection.onnx_detector import ONNXDetector

        detector = ONNXDetector(config=config)
    else:
        detector = YOLODetector(config=config)

    try:
        detector.load()
    except Exception as exc:
        logger.error("[%s] Failed to load detector: %s", camera_id, exc)
        results[camera_id] = {"error": str(exc)}
        return

    pipeline.start()

    # Extract the underlying VideoSource for EdgeProcessor compatibility
    video_source = getattr(pipeline, "_video_source", None)
    if video_source is None:
        # GStreamerPipeline doesn't wrap VideoSource; create a shim
        from apps.edge.video_source import VideoSource

        video_source = VideoSource(
            source_uri=camera_cfg.get("source", 0),
            max_queue_size=int(camera_cfg.get("max_queue_size", 2)),
            reconnect_delay_s=float(camera_cfg.get("reconnect_delay_s", 3.0)),
            name=camera_cfg.get("name", camera_id),
        )

    processor = EdgeProcessor(
        video_source=video_source,
        detector=detector,
        config=config,
    )

    try:
        processor.run()
        results[camera_id] = {"status": "completed"}
    except Exception as exc:
        logger.error("[%s] Processor error: %s", camera_id, exc)
        results[camera_id] = {"error": str(exc)}
    finally:
        pipeline.stop()
        logger.info("[%s] Camera thread done.", camera_id)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="IBVAP Multi-Camera Edge Node (Phase 8)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", default="configs/phase8_default.yaml")
    parser.add_argument("--no-display", action="store_true")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    _setup_logging(args.log_level)
    config = _load_config(args.config)
    logger.info("Config loaded: %s", args.config)

    cameras: List[dict] = config.get("cameras", [])
    if not cameras:
        logger.error("No cameras defined in config. Add a 'cameras' list.")
        sys.exit(1)

    logger.info("Starting %d camera(s)...", len(cameras))

    results: dict = {}
    threads: List[threading.Thread] = []

    for cam_cfg in cameras:
        cam_id = cam_cfg.get("id", cam_cfg.get("name", "CAM-?"))
        t = threading.Thread(
            target=_run_single_camera,
            args=(cam_cfg, config, args.no_display, results),
            name=f"cam-{cam_id}",
            daemon=True,
        )
        threads.append(t)

    # Start all camera threads
    for t in threads:
        t.start()

    logger.info("All %d camera threads started. Press Ctrl+C to stop.", len(threads))

    try:
        # Wait for all threads to complete
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt — shutting down all cameras.")

    logger.info("Multi-camera node shut down.")
    for cam_id, result in results.items():
        logger.info("  %s: %s", cam_id, result)


if __name__ == "__main__":
    main()

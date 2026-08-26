"""
apps.edge.main
---------------
CLI entry point for the IBVAP edge processing node (Laptop 1).

Usage:
    python -m apps.edge.main --config configs/phase1_default.yaml

    # Or if installed via pyproject.toml:
    ibvap-edge --config configs/phase1_default.yaml

Arguments:
    --config     Path to YAML config file (default: configs/phase1_default.yaml)
    --source     Override camera source URI (overrides config value)
    --no-display Run headless (no OpenCV window — for SSH / remote sessions)
    --log-level  Logging level: DEBUG, INFO, WARNING (default: INFO)

Phase 7 note:
    Set detector.backend: onnx in the YAML config to use the ONNX Runtime
    backend instead of PyTorch. Requires models/onnx/yolov8n.onnx (see
    scripts/export_onnx.py).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml


def _setup_logging(level: str) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


def _load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        print(f"[ERROR] Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="IBVAP Edge Processing Node",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        default="configs/phase1_default.yaml",
        help="Path to YAML config file.",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Override camera source URI (RTSP URL or local video path).",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Run headless — disable OpenCV display window.",
    )
    parser.add_argument(
        "--stream-port",
        type=int,
        default=None,
        help="Port to serve the MJPEG stream on. If set, no-display is implied.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    args = parser.parse_args()

    _setup_logging(args.log_level)
    logger = logging.getLogger("ibvap.main")

    # Load configuration
    config = _load_config(args.config)
    logger.info("Config loaded: %s", args.config)

    # Apply CLI overrides
    if args.source:
        config.setdefault("camera", {})["source"] = args.source
        logger.info("Source overridden from CLI: %s", args.source)

    if args.no_display or args.stream_port:
        config.setdefault("output", {})["display"] = False
        logger.info("Display disabled (headless or streaming mode).")
        
    if args.stream_port:
        config.setdefault("processor", {})["stream_port"] = args.stream_port
        logger.info("MJPEG Stream requested on port %d", args.stream_port)

    # Resolve camera config
    cam_cfg = config.get("camera", {})
    source_uri = cam_cfg.get("source", 0)
    max_queue_size = int(cam_cfg.get("max_queue_size", 2))
    reconnect_delay = float(cam_cfg.get("reconnect_delay_s", 3.0))
    camera_name = cam_cfg.get("name", "CAM-01")

    # Resolve detector config
    det_cfg = config.get("detector", {})
    model_path = det_cfg.get("model", "yolov8n.pt")
    device = det_cfg.get("device", "cuda:0")

    logger.info(
        "Starting edge node  source=%s  model=%s  device=%s",
        source_uri, model_path, device,
    )

    # ---- Import after arg parsing so --help is fast ----
    from apps.edge.processor import EdgeProcessor
    from apps.edge.video_source import VideoSource

    # ---- Select detector backend (Phase 7) ----
    backend = det_cfg.get("backend", "pytorch").lower()
    if backend == "onnx":
        from cv.detection.onnx_detector import ONNXDetector
        detector = ONNXDetector(config=config)
        logger.info("Using ONNX detector backend.")
    else:
        from cv.detection.yolo_detector import YOLODetector
        detector = YOLODetector(config=config)

    # Build video source
    source = VideoSource(
        source_uri=source_uri,
        max_queue_size=max_queue_size,
        reconnect_delay_s=reconnect_delay,
        name=camera_name,
    )

    # Load detector (may take a few seconds for GPU init)
    logger.info("Loading detector model...")
    detector.load()

    # Start video source
    source.start()

    # Create and run processor
    processor = EdgeProcessor(
        video_source=source,
        detector=detector,
        config=config,
    )

    try:
        processor.run()
    finally:
        source.stop()
        logger.info("Edge node shut down cleanly.")


if __name__ == "__main__":
    main()

"""
scripts/export_tensorrt.py
---------------------------
Export YOLOv8 to TensorRT FP16 engine (Phase 7 — optional).

Prerequisites:
    - NVIDIA GPU with CUDA
    - TensorRT installed (pip install tensorrt OR via NVIDIA container)
    - ONNX model already exported (run export_onnx.py first)

Usage:
    python scripts/export_tensorrt.py
    python scripts/export_tensorrt.py --model models/pytorch/yolov8n.pt --imgsz 640

Notes:
    - TRT engine files are device-specific. They cannot be transferred between
      different GPU architectures.
    - The engine is saved to models/tensorrt/ and can be referenced via the
      Ultralytics TRT integration.
    - On Windows, TensorRT may require the TRT Python bindings from NVIDIA's SDK.
      Graceful fallback is provided if TensorRT is unavailable.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scripts.export_tensorrt")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export YOLOv8 to TensorRT FP16 engine.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model",
        default="models/pytorch/yolov8n.pt",
        help="Path to the source .pt weights file.",
    )
    parser.add_argument(
        "--output-dir",
        default="models/tensorrt",
        help="Directory for the output TensorRT engine.",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Inference resolution (square).",
    )
    args = parser.parse_args()

    model_path = Path(args.model)
    output_dir = Path(args.output_dir)

    if not model_path.exists():
        logger.error("Model not found: %s", model_path)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("ultralytics is not installed. Run: pip install ultralytics")
        sys.exit(1)

    logger.info("Loading model: %s", model_path)
    model = YOLO(str(model_path))

    logger.info("Exporting to TensorRT FP16  imgsz=%d", args.imgsz)
    try:
        exported = model.export(
            format="engine",
            imgsz=args.imgsz,
            half=True,  # FP16 for RTX 4050
            device=0,  # GPU 0
            workspace=4,  # 4 GB TRT workspace (keep within 6 GB VRAM budget)
            simplify=True,
        )
        logger.info("TensorRT engine exported: %s", exported)

        # Move to output_dir if placed elsewhere
        exported_path = Path(str(exported))
        target = output_dir / exported_path.name
        if exported_path.resolve() != target.resolve():
            import shutil

            shutil.move(str(exported_path), str(target))
            logger.info("Moved to: %s", target)

        logger.info(
            "Done. Use with Ultralytics: YOLO('%s').predict(source=frame)",
            target,
        )
    except Exception as exc:
        logger.error(
            "TensorRT export failed: %s\n"
            "This is expected if TensorRT is not installed on this machine.\n"
            "Install TensorRT from: https://developer.nvidia.com/tensorrt",
            exc,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

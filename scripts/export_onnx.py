"""
scripts/export_onnx.py
-----------------------
Export a YOLOv8 PyTorch model to ONNX format (Phase 7).

Usage:
    python scripts/export_onnx.py
    python scripts/export_onnx.py --model models/pytorch/yolov8n.pt --imgsz 640
    python scripts/export_onnx.py --model models/pytorch/yolov8s.pt --output models/onnx/yolov8s.onnx

The exported ONNX model can be used with the ONNXDetector via:
    detector:
      backend: onnx
      model: models/onnx/yolov8n.onnx
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
logger = logging.getLogger("scripts.export_onnx")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export YOLOv8 PyTorch model to ONNX.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model",
        default="models/pytorch/yolov8n.pt",
        help="Path to the source .pt weights file.",
    )
    parser.add_argument(
        "--output",
        default="models/onnx/yolov8n.onnx",
        help="Path for the output .onnx file.",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Inference resolution (square). Smaller = faster, less accurate.",
    )
    parser.add_argument(
        "--half",
        action="store_true",
        help="Export FP16 ONNX (requires CUDA-capable GPU).",
    )
    args = parser.parse_args()

    model_path = Path(args.model)
    output_path = Path(args.output)

    if not model_path.exists():
        logger.error("Model not found: %s", model_path)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("ultralytics is not installed. Run: pip install ultralytics")
        sys.exit(1)

    logger.info("Loading model: %s", model_path)
    model = YOLO(str(model_path))

    logger.info(
        "Exporting to ONNX  imgsz=%d  half=%s  output=%s",
        args.imgsz,
        args.half,
        output_path,
    )
    exported = model.export(
        format="onnx",
        imgsz=args.imgsz,
        half=args.half,
        opset=17,  # ONNX opset — 17 is broadly compatible
        simplify=True,  # Graph simplification via onnx-simplifier
        dynamic=False,  # Static batch size (1) for TensorRT compatibility
    )
    logger.info("Export complete: %s", exported)

    # Move to requested output path if Ultralytics placed it elsewhere
    exported_path = Path(str(exported))
    if exported_path.resolve() != output_path.resolve():
        import shutil

        shutil.move(str(exported_path), str(output_path))
        logger.info("Moved to: %s", output_path)

    logger.info("Done. Use with: detector.backend: onnx  model: %s", output_path)


if __name__ == "__main__":
    main()

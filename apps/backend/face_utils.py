"""
apps.backend.face_utils
------------------------
Utility functions for face embedding computation using OpenCV's LBPH
(Local Binary Patterns Histograms) face recognizer.

Requirements:
    opencv-contrib-python >= 4.10  (replaces plain opencv-python)

The LBPH recognizer is CPU-only, zero-dependency, and works well as a
baseline for 1-shot face recognition across a small registry (< 200 people).
"""

from __future__ import annotations

import base64
import logging
import pickle
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ─── Embedding size (LBPH histogram length) ───────────────────────────────────
_FACE_SIZE = (64, 64)  # Resize face crop to this before computing histogram


def _decode_image(image_b64: str) -> Optional[np.ndarray]:
    """Decode a base64-encoded image string to a BGR numpy array."""
    try:
        img_bytes = base64.b64decode(image_b64)
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except Exception as exc:
        logger.error("Failed to decode base64 image: %s", exc)
        return None


def _to_gray_face(img: np.ndarray) -> Optional[np.ndarray]:
    """Convert BGR image to grayscale and resize to _FACE_SIZE."""
    if img is None or img.size == 0:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    # Use INTER_LANCZOS4 for high-quality downscale
    resized = cv2.resize(gray, _FACE_SIZE, interpolation=cv2.INTER_LANCZOS4)
    return resized


def compute_lbph_histogram(image_b64: str) -> Optional[str]:
    """
    Compute an LBPH histogram descriptor for a base64-encoded face image.

    Returns a base64-encoded pickle of the histogram ndarray, or None on failure.
    The histogram is suitable for cosine-distance matching.
    """
    img = _decode_image(image_b64)
    if img is None:
        return None

    face = _to_gray_face(img)
    if face is None:
        return None

    # LBP parameters: radius=1, neighbors=8, grid cells 8x8
    radius = 1
    neighbors = 8
    grid_x = 8
    grid_y = 8

    # Compute LBP image manually via elbp (uniform pattern)
    lbp = _compute_lbp(face, radius, neighbors)
    hist = _lbp_histogram(lbp, grid_x, grid_y, neighbors)

    # Serialize and base64-encode
    serialized = base64.b64encode(pickle.dumps(hist)).decode("utf-8")
    return serialized


def _compute_lbp(gray: np.ndarray, radius: int = 1, neighbors: int = 8) -> np.ndarray:
    """Compute the Local Binary Pattern image."""
    rows, cols = gray.shape
    output = np.zeros_like(gray, dtype=np.uint8)

    for n in range(neighbors):
        angle = 2.0 * np.pi * n / neighbors
        x = radius * np.cos(angle)
        y = -radius * np.sin(angle)

        # Bilinear interpolation coordinates
        fx = int(np.floor(x))
        fy = int(np.floor(y))
        cx = int(np.ceil(x))
        cy = int(np.ceil(y))
        tx = x - fx
        ty = y - fy

        w1 = (1 - tx) * (1 - ty)
        w2 = tx * (1 - ty)
        w3 = (1 - tx) * ty
        w4 = tx * ty

        # Safe slice with padding
        r1 = np.roll(np.roll(gray, -fy, axis=0), -fx, axis=1)
        r2 = np.roll(np.roll(gray, -fy, axis=0), -cx, axis=1)
        r3 = np.roll(np.roll(gray, -cy, axis=0), -fx, axis=1)
        r4 = np.roll(np.roll(gray, -cy, axis=0), -cx, axis=1)

        neighbor_val = w1 * r1 + w2 * r2 + w3 * r3 + w4 * r4
        output += ((neighbor_val >= gray).astype(np.uint8)) << n

    return output


def _lbp_histogram(lbp: np.ndarray, grid_x: int, grid_y: int, neighbors: int) -> np.ndarray:
    """Compute a spatial histogram of LBP codes over a grid of cells."""
    n_bins = neighbors + 2  # uniform patterns
    h, w = lbp.shape
    cell_h = h // grid_y
    cell_w = w // grid_x
    hists = []
    for gy in range(grid_y):
        for gx in range(grid_x):
            cell = lbp[gy * cell_h:(gy + 1) * cell_h, gx * cell_w:(gx + 1) * cell_w]
            hist_cell, _ = np.histogram(cell.ravel(), bins=n_bins, range=(0, n_bins))
            # L1 normalize
            norm = hist_cell.sum()
            if norm > 0:
                hist_cell = hist_cell.astype(np.float32) / norm
            hists.append(hist_cell)
    return np.concatenate(hists)


def match_histogram(
    query_b64: str,
    registry: list,  # List of dict with keys: id, name, role, embedding_b64
    threshold: float = 0.35,
) -> Optional[dict]:
    """
    Match a query face embedding (base64 pickle) against all registry entries.

    Uses cosine distance. Returns the best-match registry entry if distance < threshold,
    else None.

    Args:
        query_b64:   Base64-pickle of query histogram (from compute_lbph_histogram)
        registry:    List of face record dicts from /api/faces/embeddings
        threshold:   Maximum cosine distance to consider a match (0 = identical)

    Returns:
        The matching registry dict, or None.
    """
    if not query_b64 or not registry:
        return None

    try:
        query_hist: np.ndarray = pickle.loads(base64.b64decode(query_b64))
    except Exception:
        return None

    best_dist = float("inf")
    best_record = None

    for record in registry:
        emb_b64 = record.get("embedding_b64")
        if not emb_b64:
            continue
        try:
            cand_hist: np.ndarray = pickle.loads(base64.b64decode(emb_b64))
        except Exception:
            continue

        # Cosine distance
        dot = float(np.dot(query_hist, cand_hist))
        norm_q = float(np.linalg.norm(query_hist))
        norm_c = float(np.linalg.norm(cand_hist))
        if norm_q < 1e-9 or norm_c < 1e-9:
            continue
        cos_sim = dot / (norm_q * norm_c)
        dist = 1.0 - cos_sim

        if dist < best_dist:
            best_dist = dist
            best_record = record

    if best_record is not None and best_dist <= threshold:
        return {**best_record, "match_distance": round(best_dist, 4)}

    return None

"""
cv.face.recognition_engine
----------------------------
FaceRecognitionEngine — syncs the face registry from the backend and
identifies face crops as SOLDIER, INTRUDER, or UNKNOWN.

Architecture:
- Background thread polls GET /api/faces/embeddings every `poll_interval_s` seconds
- Per-track identity cache: once a track is identified it is not re-queried
  until the track disappears and reappears (prevents jitter)
- Uses the same LBPH histogram matching as face_utils.py (pure numpy)
- Thread-safe via a RLock around registry reads/writes

Usage (in EdgeProcessor.__init__):
    self._face_engine = FaceRecognitionEngine(
        backend_url="http://localhost:8000",
        poll_interval_s=30,
    )
    self._face_engine.start()

Usage (in EdgeProcessor._loop, after tracking):
    for det in self._last_detections:
        if det.class_name == "person" and det.track_id is not None:
            crop = _crop(frame.data, det.bbox)
            identity = self._face_engine.identify(crop)
            # identity: {"id": ..., "name": ..., "role": "SOLDIER"|"INTRUDER"|"UNKNOWN", "confidence": 0.0–1.0}
"""

from __future__ import annotations

import base64
import logging
import pickle
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_FACE_SIZE = (64, 64)
_DEFAULT_THRESHOLD = 0.40  # Cosine distance threshold (lower = stricter)


# ─── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class FaceIdentity:
    id: str
    name: str
    role: str  # "SOLDIER" | "INTRUDER" | "UNKNOWN"
    confidence: float  # 0.0 (no match) … 1.0 (perfect match)
    match_distance: float = 0.0


UNKNOWN_IDENTITY = FaceIdentity(id="", name="UNKNOWN", role="UNKNOWN", confidence=0.0)


# ─── LBPH helpers (duplicated from face_utils to avoid cross-process import) ──

def _compute_lbp(gray: np.ndarray, radius: int = 1, neighbors: int = 8) -> np.ndarray:
    output = np.zeros_like(gray, dtype=np.uint8)
    for n in range(neighbors):
        angle = 2.0 * np.pi * n / neighbors
        x = radius * np.cos(angle)
        y = -radius * np.sin(angle)
        fx, fy = int(np.floor(x)), int(np.floor(y))
        cx, cy = int(np.ceil(x)), int(np.ceil(y))
        tx, ty = x - fx, y - fy
        w1, w2, w3, w4 = (1 - tx) * (1 - ty), tx * (1 - ty), (1 - tx) * ty, tx * ty
        r1 = np.roll(np.roll(gray, -fy, axis=0), -fx, axis=1)
        r2 = np.roll(np.roll(gray, -fy, axis=0), -cx, axis=1)
        r3 = np.roll(np.roll(gray, -cy, axis=0), -fx, axis=1)
        r4 = np.roll(np.roll(gray, -cy, axis=0), -cx, axis=1)
        neighbor_val = w1 * r1 + w2 * r2 + w3 * r3 + w4 * r4
        output += ((neighbor_val >= gray).astype(np.uint8)) << n
    return output


def _lbp_histogram(lbp: np.ndarray, grid_x: int = 8, grid_y: int = 8, neighbors: int = 8) -> np.ndarray:
    n_bins = neighbors + 2
    h, w = lbp.shape
    cell_h, cell_w = h // grid_y, w // grid_x
    hists = []
    for gy in range(grid_y):
        for gx in range(grid_x):
            cell = lbp[gy * cell_h:(gy + 1) * cell_h, gx * cell_w:(gx + 1) * cell_w]
            hist_cell, _ = np.histogram(cell.ravel(), bins=n_bins, range=(0, n_bins))
            norm = hist_cell.sum()
            if norm > 0:
                hist_cell = hist_cell.astype(np.float32) / norm
            hists.append(hist_cell)
    return np.concatenate(hists)


def _face_to_histogram(face_gray: np.ndarray) -> Optional[np.ndarray]:
    """Resize, compute LBP, return L2-normalized histogram."""
    resized = cv2.resize(face_gray, _FACE_SIZE, interpolation=cv2.INTER_LANCZOS4)
    lbp = _compute_lbp(resized)
    hist = _lbp_histogram(lbp)
    norm = np.linalg.norm(hist)
    return hist / norm if norm > 1e-9 else hist


# ─── Main Engine ───────────────────────────────────────────────────────────────

class FaceRecognitionEngine:
    """
    Polls the backend for face embeddings and matches detected face crops.

    Thread safety: A single RLock protects _registry. The background sync
    thread is a daemon so it dies with the main process.
    """

    def __init__(
        self,
        backend_url: str = "http://localhost:8000",
        poll_interval_s: float = 30.0,
        match_threshold: float = _DEFAULT_THRESHOLD,
    ) -> None:
        self._backend_url = backend_url.rstrip("/")
        self._poll_interval = poll_interval_s
        self._threshold = match_threshold

        self._registry: List[dict] = []  # [{id, name, role, embedding_b64}, ...]
        self._registry_lock = threading.RLock()

        # Per-track identity cache: track_id -> FaceIdentity
        self._track_cache: Dict[int, FaceIdentity] = {}

        self._sync_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start background sync thread."""
        self._stop_event.clear()
        self._sync_thread = threading.Thread(
            target=self._sync_loop,
            name="face-registry-sync",
            daemon=True,
        )
        self._sync_thread.start()
        # Immediate first sync
        self._sync_once()
        logger.info("FaceRecognitionEngine started (backend=%s, poll=%ss)", self._backend_url, self._poll_interval)

    def stop(self) -> None:
        """Stop background sync thread."""
        self._stop_event.set()

    def invalidate_track(self, track_id: int) -> None:
        """Remove a track from the cache when it disappears."""
        self._track_cache.pop(track_id, None)

    def identify(self, face_crop_bgr: np.ndarray, track_id: Optional[int] = None) -> FaceIdentity:
        """
        Identify a face crop.

        Args:
            face_crop_bgr: BGR numpy array of the face region (can be any size).
            track_id:      If provided, uses per-track cache to avoid re-running
                           expensive matching on every frame for the same track.

        Returns:
            FaceIdentity with role SOLDIER, INTRUDER, or UNKNOWN.
        """
        # Return cached result for this track if available
        if track_id is not None and track_id in self._track_cache:
            return self._track_cache[track_id]

        identity = self._match(face_crop_bgr)

        if track_id is not None:
            self._track_cache[track_id] = identity

        return identity

    def _match(self, face_crop_bgr: np.ndarray) -> FaceIdentity:
        """Run LBPH matching against the current registry."""
        if face_crop_bgr is None or face_crop_bgr.size == 0:
            return UNKNOWN_IDENTITY

        with self._registry_lock:
            registry_snapshot = list(self._registry)

        if not registry_snapshot:
            return UNKNOWN_IDENTITY

        try:
            gray = cv2.cvtColor(face_crop_bgr, cv2.COLOR_BGR2GRAY) if len(face_crop_bgr.shape) == 3 else face_crop_bgr
            query_hist = _face_to_histogram(gray)
        except Exception as exc:
            logger.debug("Face crop preprocessing failed: %s", exc)
            return UNKNOWN_IDENTITY

        best_dist = float("inf")
        best_record = None

        for record in registry_snapshot:
            emb_b64 = record.get("embedding_b64")
            if not emb_b64:
                continue
            try:
                cand_hist: np.ndarray = pickle.loads(base64.b64decode(emb_b64))
            except Exception:
                continue

            # Cosine distance on L2-normalized histograms
            dot = float(np.dot(query_hist, cand_hist))
            norm_c = float(np.linalg.norm(cand_hist))
            if norm_c < 1e-9:
                continue
            cand_norm = cand_hist / norm_c
            cos_sim = float(np.dot(query_hist, cand_norm))
            dist = 1.0 - cos_sim

            if dist < best_dist:
                best_dist = dist
                best_record = record

        if best_record is not None and best_dist <= self._threshold:
            confidence = 1.0 - (best_dist / self._threshold)
            return FaceIdentity(
                id=best_record.get("id", ""),
                name=best_record.get("name", "UNKNOWN"),
                role=best_record.get("role", "UNKNOWN"),
                confidence=round(confidence, 3),
                match_distance=round(best_dist, 4),
            )

        return UNKNOWN_IDENTITY

    # ─── Sync thread ──────────────────────────────────────────────────────────

    def _sync_loop(self) -> None:
        """Periodically fetch updated embeddings from the backend."""
        while not self._stop_event.is_set():
            self._stop_event.wait(self._poll_interval)
            if not self._stop_event.is_set():
                self._sync_once()

    def _sync_once(self) -> None:
        """Fetch /api/faces/embeddings and update local registry."""
        try:
            import urllib.request
            url = f"{self._backend_url}/api/faces/embeddings"
            with urllib.request.urlopen(url, timeout=5) as resp:
                import json
                data = json.loads(resp.read().decode("utf-8"))
            with self._registry_lock:
                self._registry = data
            logger.debug("FaceRegistrySync: loaded %d records", len(data))
        except Exception as exc:
            logger.debug("FaceRegistrySync failed (backend unreachable?): %s", exc)

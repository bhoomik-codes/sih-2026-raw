# Project Status & Tasks

Based on the strategic context in `context.md` and an analysis of the current codebase, here is the detailed breakdown of the completion status of various phases, partially completed features, and the features yet to be implemented.

## 1. Completed Phases

*   **Phase 0: Hardware Benchmarking (M0)**
    *   **Status:** Completed
    *   **Details:** The `benchmarks/` directory contains benchmarking scripts (`phase1_benchmark.py`, `phase7_benchmark.py`, `phase8_benchmark.py`) along with CSV outputs, demonstrating that initial hardware profiling and baseline model metrics have been gathered.
*   **Phase 1: Single Camera Detection (M1)**
    *   **Status:** Completed
    *   **Details:** The `cv/detection/` module is fully implemented with `base.py`, `yolo_detector.py`, and `onnx_detector.py`. The `apps/edge/video_source.py` also handles video ingestion.
*   **Phase 2: Object Tracking (M2)**
    *   **Status:** Completed
    *   **Details:** Multi-object tracking is implemented in `cv/tracking/byte_tracker.py` and `base.py`, providing persistent track IDs.
*   **Phase 3: Event Engine (M3, M4)**
    *   **Status:** Completed
    *   **Details:** The core logic for spatial and temporal events is fully implemented in `intelligence/events/`, including `virtual_fence.py`, `line_crossing.py`, `loitering.py`, and `night_activity.py`.
*   **Phase 4: Incident & Risk Engine (M5)**
    *   **Status:** Completed
    *   **Details:** The `intelligence/risk/scorer.py` and `intelligence/incidents/generator.py` are implemented to correlate events and assign risk scores, generating actionable incidents.
*   **Phase 7: TensorRT Optimization (M9)**
    *   **Status:** Completed
    *   **Details:** `scripts/export_tensorrt.py` and `benchmarks/phase7_benchmark.py` exist, confirming that model optimization to TensorRT/FP16 is functional.

## 2. Partially Complete Phases

*   **Phase 5: Vehicle Intelligence and ANPR (M7)**
    *   **Status:** Partially Complete
    *   **Details:** The logical engine (`intelligence/anpr/engine.py`) is implemented and supports buffer logic for OCR to save GPU resources. However, it relies on a mock mode fallback if `easyocr` is missing, and the `cv/anpr` directory remains empty (contains only `.gitkeep`), suggesting the CV pipeline side for ANPR might need further integration.
*   **Phase 6: Night-Time Performance (M8)**
    *   **Status:** Partially Complete
    *   **Details:** While `intelligence/events/night_activity.py` and its corresponding tests are implemented, low-light image enhancement techniques (e.g., in `cv/preprocessing/frame_prep.py`) or specialized night-time model fine-tuning may not be fully integrated.
*   **Phase 9: Command Center (M11)**
    *   **Status:** Partially Complete
    *   **Details:** The `apps/dashboard/` exists as a Vite/React project, and `apps/backend/` has a FastAPI backend (`main.py`, `db.py`). It is functional but likely needs full WebSocket integration with the AI Edge Processing Node (`apps/edge/`) for real-time live events.
*   **Phase 10: Hardening & Bug Testing**
    *   **Status:** Partially Complete
    *   **Details:** A comprehensive test suite exists (`tests/` directory with `test_detection.py`, `test_event_engine.py`, etc.), but end-to-end multi-camera stability, thermal testing, and RTSP watchdog recovery are likely still ongoing.

## 3. Features Yet to Be Implemented

*   **Phase 8: DeepStream Migration (M10)**
    *   **Status:** Not Implemented
    *   **Details:** The `pipelines/deepstream/` directory is essentially empty (`.gitkeep` and a stub `__init__.py`). The migration to NVIDIA DeepStream for the production video pipeline has not started.
*   **Phase 11: Competition Demo Build (M12)**
    *   **Status:** Not Implemented
    *   **Details:** The final feature freeze and polished end-to-end demo build for the presentation has yet to be assembled.
*   **Face Detection**
    *   **Status:** Not Implemented (Low Priority)
    *   **Details:** `cv/face/` contains only `.gitkeep`. As per the rules in `context.md`, this is an optional feature and should not block core functionality.

## 4. Next Action Items

- [ ] **ANPR Integration:** Finalize the ANPR computer vision pipeline in `cv/anpr/` and ensure integration with `intelligence/anpr/engine.py` using hardware acceleration instead of mock mode.
- [ ] **DeepStream Pipeline:** Begin experimenting with DeepStream pipelines (`pipelines/deepstream/`) to validate if it can handle multi-camera load more efficiently than the current OpenCV/GStreamer implementations.
- [ ] **Command Center Integration:** Ensure that `apps/edge/` successfully transmits WebSocket events (Risk Scores, Incidents) to `apps/backend/`, and verify the `apps/dashboard/` visually reflects these alerts in real-time.
- [ ] **Command Center UI:** Map view with Leaflet camera pins + incident markers (Leaflet CSS is in index.css), and a risk score sparkline on the command center header.
- [ ] **Fix Known Issues:** Resolve the memory leak in ByteTrack (`cv/tracking/byte_tracker.py`), the OpenCV blocking read issue in `apps/edge/video_source.py`, and the sequential timeout delay in `apps/edge/multi_camera_manager.py`.

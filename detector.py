"""
detector.py – Fruit size detector with YOLOv8-nano primary + OpenCV fallback.

Strategy:
  1. If USE_YOLO is True, run YOLOv8-nano on the frame.
     - If a matching class (or any class if produce has no COCO mapping) is found,
       use its bounding box to compute the fruit size in mm.
  2. If YOLO finds nothing (or USE_YOLO is False), fall back to OpenCV
     area-ratio contour detection.

Usage:
    from detector import FruitSizeDetector
    det = FruitSizeDetector()
    size_mm = det.measure(frame_bgr, produce_name="Orange")
"""

import logging
import cv2
import numpy as np

from config import (
    PIXELS_PER_MM,
    USE_YOLO,
    YOLO_MODEL,
    YOLO_CONFIDENCE,
    YOLO_CLASS_MAP,
)

log = logging.getLogger(__name__)

# Minimum YOLO confidence – use config value but with a safe lower fallback
_YOLO_CONF = min(YOLO_CONFIDENCE, 0.20)  # never higher than 0.20 for detection robustness


class FruitSizeDetector:
    def __init__(self):
        self._yolo = None
        if USE_YOLO:
            try:
                # Import here so OpenCV-only mode never requires ultralytics
                from ultralytics import YOLO  # noqa: PLC0415
                log.info(f"Loading YOLO model: {YOLO_MODEL}")
                self._yolo = YOLO(YOLO_MODEL)
                log.info("YOLO model loaded successfully")
            except Exception as e:
                log.warning(f"YOLO failed to load ({e}) – falling back to OpenCV only")

    # ── Public API ────────────────────────────────────────────────────────────

    def measure(self, frame_bgr: np.ndarray, produce_name: str = "") -> float:
        """
        Measure the fruit's size in mm using YOLO (if enabled) or OpenCV.

        Returns the larger dimension of the fruit's bounding box in mm.
        Returns 0.0 if no fruit is detected.
        """
        if self._yolo is not None:
            size = self._measure_yolo(frame_bgr, produce_name)
            if size > 0.0:
                return size
            log.info("YOLO found nothing – falling back to OpenCV contour")

        return self._measure_opencv(frame_bgr)

    # ── YOLO detection ────────────────────────────────────────────────────────

    def _measure_yolo(self, frame_bgr: np.ndarray, produce_name: str) -> float:
        """Run YOLOv8 and return size_mm from the best matching bounding box."""
        target_class = YOLO_CLASS_MAP.get(produce_name)  # may be None

        try:
            results = self._yolo(frame_bgr, conf=_YOLO_CONF, verbose=False)
        except Exception as e:
            log.warning(f"YOLO inference error: {e}")
            return 0.0

        if not results or results[0].boxes is None:
            log.info("YOLO: no detections")
            return 0.0

        boxes = results[0].boxes
        names = results[0].names  # {class_id: class_name}

        best_box  = None
        best_area = 0

        for box in boxes:
            cls_id    = int(box.cls[0])
            cls_name  = names.get(cls_id, "")
            conf      = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            area = (x2 - x1) * (y2 - y1)

            # If produce has a COCO class, only accept matching detections
            if target_class is not None and cls_name.lower() != target_class.lower():
                continue

            log.info(
                f"YOLO detected: {cls_name}  conf={conf:.2f}  "
                f"bbox=({x1},{y1})→({x2},{y2})  area={area}"
            )

            if area > best_area:
                best_area = area
                best_box  = (x1, y1, x2, y2)

        if best_box is None:
            if target_class:
                log.info(f"YOLO: no '{target_class}' detected above conf {YOLO_CONFIDENCE}")
            else:
                log.info("YOLO: no detections passed filter")
            return 0.0

        x1, y1, x2, y2 = best_box
        w_px   = x2 - x1
        h_px   = y2 - y1
        size_px = max(w_px, h_px)
        size_mm = round(size_px / PIXELS_PER_MM, 1)
        log.info(
            f"YOLO size: w={w_px}px h={h_px}px  →  {size_px}px"
            f" / {PIXELS_PER_MM} px/mm  =  {size_mm} mm"
        )
        return size_mm

    # ── OpenCV fallback ───────────────────────────────────────────────────────

    def _measure_opencv(self, frame_bgr: np.ndarray) -> float:
        """
        Detect the fruit contour with Otsu thresholding.

        Filters (applied together):
          - Area must be 2%–85% of frame  (removes noise and full-frame blobs)
          - Width  must be < 90% of frame width   (removes horizon-wide streaks)
          - Height must be < 90% of frame height  (removes full-height artifacts)
          - Aspect ratio between 0.3 and 3.0  (roughly fruit-shaped)
        Tries normal then inverted threshold.
        """
        h_img, w_img = frame_bgr.shape[:2]
        frame_area   = h_img * w_img
        MIN_AREA     = 0.02 * frame_area
        MAX_AREA     = 0.85 * frame_area
        MAX_W        = 0.90 * w_img      # contour must NOT span 90%+ of frame width
        MAX_H        = 0.90 * h_img      # contour must NOT span 90%+ of frame height

        gray    = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        for inv in (False, True):
            flags = (cv2.THRESH_BINARY_INV if inv else cv2.THRESH_BINARY) + cv2.THRESH_OTSU
            thresh_val, thresh = cv2.threshold(blurred, 0, 255, flags)
            log.debug(f"OpenCV Otsu: {thresh_val:.1f}  inverted={inv}")

            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            log.info(f"OpenCV contours found: {len(contours)}  inverted={inv}")

            candidates = []
            for c in contours:
                area = cv2.contourArea(c)
                if not (MIN_AREA <= area <= MAX_AREA):
                    continue
                _, _, cw, ch = cv2.boundingRect(c)
                if cw >= MAX_W or ch >= MAX_H:
                    log.debug(f"  Skipped contour {cw}×{ch}px (spans too much of frame)")
                    continue
                ar = cw / ch if ch > 0 else 0
                if not (0.3 <= ar <= 3.0):
                    log.debug(f"  Skipped contour aspect ratio {ar:.2f} (not fruit-shaped)")
                    continue
                candidates.append(c)

            if not candidates:
                log.warning(
                    f"OpenCV: no valid fruit contours after all filters (inverted={inv})"
                )
                continue

            largest  = max(candidates, key=cv2.contourArea)
            area     = cv2.contourArea(largest)
            _, _, w_px, h_px = cv2.boundingRect(largest)
            # Use width as primary dimension (height can clip at frame edge)
            size_px  = w_px
            size_mm  = round(size_px / PIXELS_PER_MM, 1)
            log.info(
                f"OpenCV size: area={area:.0f}px²  w={w_px}px h={h_px}px"
                f"  →  {size_px}px / {PIXELS_PER_MM} px/mm  =  {size_mm} mm"
            )
            return size_mm

        log.warning("OpenCV: could not isolate a fruit contour – returning 0.0")
        return 0.0

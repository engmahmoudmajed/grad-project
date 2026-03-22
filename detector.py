"""
detector.py – Fruit size detector with YOLOv8-nano primary + OpenCV fallback.

Strategy:
  1. If USE_YOLO is True, run YOLOv8-nano on the frame.
     - If a matching class (or any class if produce has no COCO mapping) is found,
       use its bounding box to compute the fruit size in mm.
  2. If YOLO finds nothing (or USE_YOLO is False), fall back to OpenCV
     contour detection with tight filtering.

Returns a measurement dict with width_mm, height_mm, diameter_mm, and volume_cm3.

Usage:
    from detector import FruitSizeDetector
    det = FruitSizeDetector()
    result = det.measure(frame_bgr, produce_name="Orange")
    # result = {"width_mm": 72.5, "height_mm": 68.3, "diameter_mm": 72.5, "volume_cm3": 198.4}
    # or None if no fruit detected
"""

import math
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
_YOLO_CONF = min(YOLO_CONFIDENCE, 0.20)


def _estimate_volume_cm3(width_mm: float, height_mm: float) -> float:
    """
    Estimate fruit volume in cm³ using an ellipsoid model.

    Approximates the fruit as an ellipsoid with three radii:
      rx = width / 2
      ry = height / 2
      rz = min(width, height) / 2   (depth ≈ smaller visible dimension)

    Volume = (4/3) × π × rx × ry × rz   (in mm³, converted to cm³)
    """
    rx = width_mm / 2.0
    ry = height_mm / 2.0
    rz = min(width_mm, height_mm) / 2.0
    volume_mm3 = (4.0 / 3.0) * math.pi * rx * ry * rz
    return round(volume_mm3 / 1000.0, 1)


def _make_result(w_px: int, h_px: int) -> dict:
    """Build a measurement dict from pixel dimensions."""
    width_mm  = round(w_px / PIXELS_PER_MM, 1)
    height_mm = round(h_px / PIXELS_PER_MM, 1)
    diameter_mm = round(max(w_px, h_px) / PIXELS_PER_MM, 1)
    volume_cm3  = _estimate_volume_cm3(width_mm, height_mm)
    return {
        "width_mm":    width_mm,
        "height_mm":   height_mm,
        "diameter_mm": diameter_mm,
        "volume_cm3":  volume_cm3,
    }


class FruitSizeDetector:
    def __init__(self):
        self._yolo = None
        if USE_YOLO:
            try:
                from ultralytics import YOLO  # noqa: PLC0415
                log.info(f"Loading YOLO model: {YOLO_MODEL}")
                self._yolo = YOLO(YOLO_MODEL)
                log.info("YOLO model loaded successfully")
            except Exception as e:
                log.warning(f"YOLO failed to load ({e}) – falling back to OpenCV only")

    # ── Public API ────────────────────────────────────────────────────────────

    def measure(self, frame_bgr: np.ndarray, produce_name: str = "") -> dict | None:
        """
        Measure the fruit's size using YOLO (if enabled) or OpenCV.

        Returns a dict:
            {"width_mm", "height_mm", "diameter_mm", "volume_cm3"}
        or None if no fruit is detected.
        """
        if self._yolo is not None:
            result = self._measure_yolo(frame_bgr, produce_name)
            if result is not None:
                return result
            log.info("YOLO found nothing – falling back to OpenCV contour")

        return self._measure_opencv(frame_bgr)

    # ── YOLO detection ────────────────────────────────────────────────────────

    def _measure_yolo(self, frame_bgr: np.ndarray, produce_name: str) -> dict | None:
        """Run YOLOv8 and return measurement dict from the best matching bbox."""
        target_class = YOLO_CLASS_MAP.get(produce_name)  # may be None

        try:
            results = self._yolo(frame_bgr, conf=_YOLO_CONF, verbose=False)
        except Exception as e:
            log.warning(f"YOLO inference error: {e}")
            return None

        if not results or results[0].boxes is None:
            log.info("YOLO: no detections")
            return None

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

            # If produce has a COCO class, only accept matching detections;
            # if no COCO mapping (None), accept ANY detection
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
            return None

        x1, y1, x2, y2 = best_box
        w_px = x2 - x1
        h_px = y2 - y1
        result = _make_result(w_px, h_px)
        log.info(
            f"YOLO size: {w_px}×{h_px}px → "
            f"w={result['width_mm']}mm  h={result['height_mm']}mm  "
            f"Ø={result['diameter_mm']}mm  vol={result['volume_cm3']}cm³"
        )
        return result

    # ── OpenCV fallback ───────────────────────────────────────────────────────

    def _measure_opencv(self, frame_bgr: np.ndarray) -> dict | None:
        """
        Detect the fruit contour using multiple strategies:
          1. HSV color-based segmentation (best for colorful fruit)
          2. Otsu thresholding fallback (for less colorful produce)

        Filters:
          - Area must be 2%–35% of frame  (fruit is a small-to-medium object)
          - Width  must be < 50% of frame width
          - Height must be < 50% of frame height
          - Aspect ratio between 0.3 and 3.0  (roughly fruit-shaped)
        """
        h_img, w_img = frame_bgr.shape[:2]
        frame_area   = h_img * w_img
        MIN_AREA     = 0.01 * frame_area    # at least 1% of frame
        MAX_AREA     = 0.35 * frame_area    # at most 35% (was 85% – too loose)
        MAX_W        = 0.50 * w_img         # max 50% of width (was 90%)
        MAX_H        = 0.50 * h_img         # max 50% of height (was 90%)

        # ── Strategy 1: HSV color segmentation ─────────────────────────────
        result = self._try_hsv_segmentation(frame_bgr, MIN_AREA, MAX_AREA, MAX_W, MAX_H)
        if result is not None:
            return result

        # ── Strategy 2: Otsu thresholding with morphological cleanup ───────
        result = self._try_otsu_threshold(frame_bgr, MIN_AREA, MAX_AREA, MAX_W, MAX_H)
        if result is not None:
            return result

        log.warning("OpenCV: could not isolate a fruit contour – returning None")
        return None

    def _try_hsv_segmentation(self, frame_bgr, min_area, max_area, max_w, max_h) -> dict | None:
        """
        Use HSV color space to find the fruit.
        Looks for warm-colored objects (red, orange, yellow, green).
        """
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)

        # Multiple color ranges for common fruit colors
        masks = []

        # Red/orange range 1 (low hue: 0-15)
        masks.append(cv2.inRange(hsv, (0, 50, 50), (15, 255, 255)))
        # Red range 2 (high hue: 165-180, wraps around)
        masks.append(cv2.inRange(hsv, (165, 50, 50), (180, 255, 255)))
        # Orange/yellow range (15-35)
        masks.append(cv2.inRange(hsv, (15, 50, 50), (35, 255, 255)))
        # Yellow/green range (35-85)
        masks.append(cv2.inRange(hsv, (35, 40, 50), (85, 255, 255)))

        # Combine all masks
        combined = masks[0]
        for m in masks[1:]:
            combined = cv2.bitwise_or(combined, m)

        # Clean up noise with morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel, iterations=1)

        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        log.info(f"HSV contours found: {len(contours)}")

        best = self._pick_best_contour(contours, min_area, max_area, max_w, max_h)
        if best is not None:
            _, _, w_px, h_px = cv2.boundingRect(best)
            result = _make_result(w_px, h_px)
            log.info(
                f"HSV size: {w_px}×{h_px}px → "
                f"w={result['width_mm']}mm  h={result['height_mm']}mm  "
                f"Ø={result['diameter_mm']}mm  vol={result['volume_cm3']}cm³"
            )
            return result

        log.info("HSV: no valid fruit contour found")
        return None

    def _try_otsu_threshold(self, frame_bgr, min_area, max_area, max_w, max_h) -> dict | None:
        """Otsu thresholding with morphological cleanup."""
        gray    = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        for inv in (False, True):
            flags = (cv2.THRESH_BINARY_INV if inv else cv2.THRESH_BINARY) + cv2.THRESH_OTSU
            thresh_val, thresh = cv2.threshold(blurred, 0, 255, flags)
            log.debug(f"Otsu: {thresh_val:.1f}  inverted={inv}")

            # Morphological cleanup to remove noise and merge close regions
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            log.info(f"Otsu contours: {len(contours)}  inverted={inv}")

            best = self._pick_best_contour(contours, min_area, max_area, max_w, max_h)
            if best is not None:
                _, _, w_px, h_px = cv2.boundingRect(best)
                result = _make_result(w_px, h_px)
                log.info(
                    f"Otsu size: {w_px}×{h_px}px → "
                    f"w={result['width_mm']}mm  h={result['height_mm']}mm  "
                    f"Ø={result['diameter_mm']}mm  vol={result['volume_cm3']}cm³"
                )
                return result

        return None

    def _pick_best_contour(self, contours, min_area, max_area, max_w, max_h):
        """
        From a list of contours, pick the best fruit candidate.

        Prefers contours that are:
          - Within the area limits
          - Within the size limits
          - Most circular (closest to aspect ratio 1.0)
        """
        candidates = []
        for c in contours:
            area = cv2.contourArea(c)
            if not (min_area <= area <= max_area):
                continue
            _, _, cw, ch = cv2.boundingRect(c)
            if cw >= max_w or ch >= max_h:
                log.debug(f"  Skipped contour {cw}×{ch}px (too large for frame)")
                continue
            ar = cw / ch if ch > 0 else 0
            if not (0.3 <= ar <= 3.0):
                log.debug(f"  Skipped contour aspect ratio {ar:.2f}")
                continue
            # Score by circularity: closer to 1.0 aspect ratio = more likely fruit
            circularity = min(ar, 1.0 / ar) if ar > 0 else 0
            candidates.append((circularity, area, c))

        if not candidates:
            return None

        # Sort by circularity first (prefer round), then by area (prefer larger)
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        _, _, best = candidates[0]
        return best

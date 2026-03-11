"""
camera.py – Dual-camera fruit capture and size measurement.

Opens BOTH Pi cameras (ov5647 + imx219), captures from both when triggered,
runs FruitSizeDetector on each frame, and uses the best detection.
If one camera fails to open, gracefully falls back to the other.

Usage:
    from camera import Camera
    cam = Camera()
    size_mm, image_path = cam.capture_and_measure(produce_name="Orange")
    cam.close()
"""

import os
import logging
import cv2
import numpy as np
from picamera2 import Picamera2

from config import CAPTURE_PATH
from detector import FruitSizeDetector

log = logging.getLogger(__name__)

# Paths for saving each camera's capture (for debugging)
_CAM0_PATH = CAPTURE_PATH.replace(".jpg", "_cam0.jpg")
_CAM1_PATH = CAPTURE_PATH.replace(".jpg", "_cam1.jpg")


class Camera:
    def __init__(self):
        os.makedirs(os.path.dirname(CAPTURE_PATH) or ".", exist_ok=True)

        self._cams = []       # list of (Picamera2, label, save_path)
        self._detector = FruitSizeDetector()

        # Try to open Camera 0 (ov5647)
        try:
            cam0 = Picamera2(0)
            cfg0 = cam0.create_still_configuration(
                main={"size": (1920, 1080), "format": "RGB888"}
            )
            cam0.configure(cfg0)
            cam0.start()
            self._cams.append((cam0, "cam0-ov5647", _CAM0_PATH))
            log.info("Camera 0 (ov5647) opened successfully")
        except Exception as e:
            log.warning(f"Camera 0 (ov5647) failed to open: {e}")

        # Try to open Camera 1 (imx219)
        try:
            cam1 = Picamera2(1)
            cfg1 = cam1.create_still_configuration(
                main={"size": (1920, 1080), "format": "RGB888"}
            )
            cam1.configure(cfg1)
            cam1.start()
            self._cams.append((cam1, "cam1-imx219", _CAM1_PATH))
            log.info("Camera 1 (imx219) opened successfully")
        except Exception as e:
            log.warning(f"Camera 1 (imx219) failed to open: {e}")

        if not self._cams:
            raise RuntimeError("No cameras could be opened!")

        log.info(f"Dual-camera ready: {len(self._cams)} camera(s) active")

    # ── Public API ────────────────────────────────────────────────────────────

    def capture_and_measure(self, produce_name: str = "") -> tuple[float, str]:
        """
        Capture from ALL available cameras, run detection on each, and use
        the best result (highest measured size > 0).

        Returns:
            (size_mm, image_path)
        """
        best_size = 0.0
        best_path = CAPTURE_PATH

        for cam, label, save_path in self._cams:
            try:
                frame_rgb = cam.capture_array()
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                cv2.imwrite(save_path, frame_bgr)

                size_mm = self._detector.measure(frame_bgr, produce_name)
                log.info(f"[{label}] measured: {size_mm} mm")

                if size_mm > best_size:
                    best_size = size_mm
                    best_path = save_path
            except Exception as e:
                log.error(f"[{label}] capture error: {e}")

        # Copy best image to main capture path
        if best_path != CAPTURE_PATH and os.path.exists(best_path):
            import shutil
            shutil.copy2(best_path, CAPTURE_PATH)

        return best_size, CAPTURE_PATH

    def close(self) -> None:
        """Stop all cameras."""
        for cam, label, _ in self._cams:
            try:
                cam.stop()
                cam.close()
                log.info(f"[{label}] closed")
            except Exception as e:
                log.warning(f"[{label}] close error: {e}")

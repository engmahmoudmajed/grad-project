"""
camera.py – Dual-camera fruit capture and size measurement.

Opens BOTH Pi cameras (ov5647 + imx219), runs continuous background capture
threads that save frames to /tmp/ for the monitor server, and provides
capture_and_measure() for the main event loop.

Architecture:
  - Each camera has a background thread that captures at ~10 fps
  - Frames are saved to /tmp/fruit_capture_cam0.jpg and cam1.jpg
  - The monitor server reads these files and streams them via MJPEG
  - capture_and_measure() grabs the latest buffered frame (no contention)

Usage:
    from camera import Camera
    cam = Camera()
    result, img_path = cam.capture_and_measure(produce_name="Orange")
    cam.close()
"""

import os
import time
import logging
import threading
import cv2
import numpy as np
from picamera2 import Picamera2

from config import CAPTURE_PATH
from detector import FruitSizeDetector

log = logging.getLogger(__name__)

# Paths for saving each camera's capture (for monitor server + debugging)
_CAM0_PATH = CAPTURE_PATH.replace(".jpg", "_cam0.jpg")
_CAM1_PATH = CAPTURE_PATH.replace(".jpg", "_cam1.jpg")

# Background capture rate
_CAPTURE_INTERVAL = 0.10  # 10 fps


def _combine_measurements(measurements: list[dict]) -> dict | None:
    """
    Combine measurements from multiple cameras smartly.

    - If only one camera detected: use it directly.
    - If both cameras detected and results are similar (within 50%): average them.
    - If both detected but results differ a lot (>50%): use the SMALLER one.
      (Background blobs tend to be larger than the actual fruit.)
    """
    n = len(measurements)
    if n == 0:
        return None
    if n == 1:
        return measurements[0]

    # Check if measurements are consistent
    diameters = [m["diameter_mm"] for m in measurements]
    d_min, d_max = min(diameters), max(diameters)

    if d_min > 0 and (d_max / d_min) > 1.5:
        # Measurements differ by >50% — trust the smaller one
        # (background blobs are typically larger than the fruit)
        import logging
        log = logging.getLogger(__name__)
        log.warning(
            f"Camera measurements differ a lot ({d_min:.0f}mm vs {d_max:.0f}mm) "
            f"– using smaller (more likely fruit)"
        )
        smallest = min(measurements, key=lambda m: m["diameter_mm"])
        return smallest

    # Measurements are consistent — average them
    avg = {}
    for key in ("width_mm", "height_mm", "diameter_mm", "volume_cm3"):
        values = [m[key] for m in measurements]
        avg[key] = round(sum(values) / n, 1)
    return avg


class Camera:
    def __init__(self):
        os.makedirs(os.path.dirname(CAPTURE_PATH) or ".", exist_ok=True)

        self._cams = []          # list of (Picamera2, label, save_path)
        self._detector = FruitSizeDetector()
        self._running = True

        # Per-camera latest frame buffer (protected by lock)
        self._frames = {}        # label -> latest BGR frame (numpy array)
        self._frame_locks = {}   # label -> threading.Lock

        # Try to open Camera 0 (imx219)
        try:
            cam0 = Picamera2(0)
            cfg0 = cam0.create_still_configuration(
                main={"size": (1920, 1080), "format": "RGB888"}
            )
            cam0.configure(cfg0)
            cam0.start()
            self._cams.append((cam0, "cam0-imx219", _CAM0_PATH))
            log.info("Camera 0 (imx219) opened successfully")
        except Exception as e:
            log.warning(f"Camera 0 (imx219) failed to open: {e}")

        # Try to open Camera 1 (ov5647)
        try:
            cam1 = Picamera2(1)
            cfg1 = cam1.create_still_configuration(
                main={"size": (1920, 1080), "format": "RGB888"}
            )
            cam1.configure(cfg1)
            cam1.start()
            self._cams.append((cam1, "cam1-ov5647", _CAM1_PATH))
            log.info("Camera 1 (ov5647) opened successfully")
        except Exception as e:
            log.warning(f"Camera 1 (ov5647) failed to open: {e}")

        if not self._cams:
            raise RuntimeError("No cameras could be opened!")

        log.info(f"Dual-camera ready: {len(self._cams)} camera(s) active")

        # Start background capture threads
        for cam, label, save_path in self._cams:
            lock = threading.Lock()
            self._frame_locks[label] = lock
            self._frames[label] = None
            t = threading.Thread(
                target=self._capture_loop,
                args=(cam, label, save_path, lock),
                daemon=True,
            )
            t.start()
            log.info(f"[{label}] background capture thread started")

    # ── Background capture loop ──────────────────────────────────────────────

    def _capture_loop(self, cam, label, save_path, lock):
        """
        Continuously capture frames from one camera.
        Saves to disk (for monitor server) and keeps latest in memory.
        """
        while self._running:
            try:
                frame_rgb = cam.capture_array()
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

                # Update in-memory buffer
                with lock:
                    self._frames[label] = frame_bgr

                # Save to disk so monitor server can stream it
                cv2.imwrite(save_path, frame_bgr,
                            [cv2.IMWRITE_JPEG_QUALITY, 85])

            except Exception as e:
                log.error(f"[{label}] capture loop error: {e}")
                time.sleep(0.5)

            time.sleep(_CAPTURE_INTERVAL)

    # ── Public API ────────────────────────────────────────────────────────────

    def capture_and_measure(self, produce_name: str = "") -> tuple[dict | None, str]:
        """
        Grab the latest frame from ALL cameras, run detection on each, and
        average the results for better accuracy.

        Uses the buffered frames from background threads — no contention
        with the capture loop.

        Returns:
            (measurement_dict, image_path)
            measurement_dict has: width_mm, height_mm, diameter_mm, volume_cm3
            or None if no fruit detected on any camera.
        """
        measurements = []
        best_path = CAPTURE_PATH

        for _cam, label, save_path in self._cams:
            # Grab the latest frame from the background buffer
            with self._frame_locks[label]:
                frame = self._frames.get(label)

            if frame is None:
                log.warning(f"[{label}] no frame buffered yet")
                continue

            # Make a copy so the background thread can keep writing
            frame_bgr = frame.copy()

            # Save a high-quality version for the detection result
            cv2.imwrite(save_path, frame_bgr)

            result = self._detector.measure(frame_bgr, produce_name)

            if result is not None:
                log.info(
                    f"[{label}] Ø={result['diameter_mm']}mm  "
                    f"w={result['width_mm']}mm  h={result['height_mm']}mm  "
                    f"vol={result['volume_cm3']}cm³"
                )
                measurements.append(result)
                best_path = save_path
            else:
                log.warning(f"[{label}] no fruit detected")

        # Average all successful measurements
        avg = _combine_measurements(measurements)

        if avg is not None:
            log.info(
                f"Averaged ({len(measurements)} cam): "
                f"Ø={avg['diameter_mm']}mm  vol={avg['volume_cm3']}cm³"
            )

        # Copy best image to main capture path
        if best_path != CAPTURE_PATH and os.path.exists(best_path):
            import shutil
            shutil.copy2(best_path, CAPTURE_PATH)

        return avg, CAPTURE_PATH

    def close(self) -> None:
        """Stop all cameras and background threads."""
        self._running = False
        time.sleep(0.3)  # let capture loops finish
        for cam, label, _ in self._cams:
            try:
                cam.stop()
                cam.close()
                log.info(f"[{label}] closed")
            except Exception as e:
                log.warning(f"[{label}] close error: {e}")

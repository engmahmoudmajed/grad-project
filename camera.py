"""
camera.py – Fruit image capture and size measurement.

Uses picamera2 to capture a still, then OpenCV to find the largest contour
(the fruit) and measure its bounding box.  The pixel measurement is converted
to millimetres using PIXELS_PER_MM from config.py.

Usage:
    from camera import Camera
    cam = Camera()
    size_mm, image_path = cam.capture_and_measure()
    cam.close()
"""

import cv2
import numpy as np
from picamera2 import Picamera2

from config import CAPTURE_PATH, PIXELS_PER_MM


class Camera:
    def __init__(self):
        self._cam = Picamera2()
        config = self._cam.create_still_configuration(
            main={"size": (1920, 1080), "format": "RGB888"}
        )
        self._cam.configure(config)
        self._cam.start()

    # ── Public API ────────────────────────────────────────────────────────────

    def capture_and_measure(self) -> tuple[float, str]:
        """
        Capture one frame, detect the fruit contour, and measure its size.

        Returns:
            (size_mm, image_path)
            size_mm    – the larger dimension of the fruit bounding box in mm.
                         Returns 0.0 if no contour was found.
            image_path – path where the captured image was saved.
        """
        frame_rgb = self._cam.capture_array()
        # picamera2 returns RGB; OpenCV uses BGR
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        cv2.imwrite(CAPTURE_PATH, frame_bgr)

        size_mm = self._measure_size(frame_bgr)
        return size_mm, CAPTURE_PATH

    def close(self) -> None:
        """Stop the camera (call on exit)."""
        self._cam.stop()
        self._cam.close()

    # ── Private ───────────────────────────────────────────────────────────────

    def _measure_size(self, frame_bgr: np.ndarray) -> float:
        """
        Detect the largest non-background contour and return the larger of its
        bounding-box width/height converted to mm.

        Strategy:
          1. Convert to grayscale and apply Gaussian blur.
          2. Binary threshold (dark conveyor belt → easy to threshold fruit).
          3. Find contours; pick the largest by area.
          4. Get bounding rect and convert pixels → mm.
        """
        gray   = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        # Otsu's binarisation works well for bi-modal (fruit vs belt) histograms
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return 0.0

        largest = max(contours, key=cv2.contourArea)

        # Minimum area guard – ignore tiny noise
        if cv2.contourArea(largest) < 500:
            return 0.0

        _, _, w_px, h_px = cv2.boundingRect(largest)
        # Use the larger dimension as the representative measurement
        size_px = max(w_px, h_px)
        size_mm = size_px / PIXELS_PER_MM
        return round(size_mm, 1)

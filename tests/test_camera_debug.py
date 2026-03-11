"""
tests/test_camera_debug.py – Standalone camera + detector diagnostic.

Run from the project root with the venv activated:
    python tests/test_camera_debug.py [produce_name]

Examples:
    python tests/test_camera_debug.py Orange
    python tests/test_camera_debug.py Apple

What it does:
  1. Captures a single frame and saves it
  2. Runs FruitSizeDetector (YOLO → OpenCV fallback) and prints result
  3. Classifies the size for all produce types
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
from picamera2 import Picamera2

from config import CAPTURE_PATH, PRODUCE_NAMES
from detector import FruitSizeDetector
from classifier import classify_info

DEBUG_IMG_PATH = CAPTURE_PATH.replace(".jpg", "_debug.jpg")


def capture_frame() -> "cv2.Mat":
    cam = Picamera2()
    cfg = cam.create_still_configuration(main={"size": (1920, 1080), "format": "RGB888"})
    cam.configure(cfg)
    cam.start()
    import cv2
    frame_rgb = cam.capture_array()
    cam.stop()
    cam.close()
    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(CAPTURE_PATH, frame_bgr)
    print(f"[✓] Image saved: {CAPTURE_PATH}")
    return frame_bgr


def classify_all(size_mm: float) -> None:
    print("\n--- Classification for all produce types ---")
    print(f"{'Idx':<5} {'Name':<14} Category")
    print("-" * 35)
    for idx, name in enumerate(PRODUCE_NAMES):
        info = classify_info(size_mm, idx)
        print(f"  {idx:<4} {name:<14} {info['category']}")


if __name__ == "__main__":
    produce = sys.argv[1] if len(sys.argv) > 1 else ""
    print("=" * 55)
    print(f"  Camera + Detector Diagnostic  (produce={produce or 'any'})")
    print("=" * 55)

    frame = capture_frame()
    det   = FruitSizeDetector()
    size  = det.measure(frame, produce_name=produce)

    print(f"\n[RESULT] Measured size: {size} mm")
    if size > 0:
        classify_all(size)
    else:
        print("[!] Size = 0.0 – fruit not detected.")
        print("    Tips:")
        print("    • Ensure the fruit is clearly visible in the frame")
        print("    • Try better lighting for contrast")
        print("    • Lower YOLO_CONFIDENCE in config.py (e.g. 0.25)")

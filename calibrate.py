"""
calibrate.py – One-shot PIXELS_PER_MM calibration for the Fruit Classification System.

HOW TO USE:
  1. Place a flat object of known width (e.g. a ruler, coin, credit card) under the camera
     in the same position where fruit normally sits on the belt.
  2. Run:   python calibrate.py
  3. Enter the actual width of the object in mm when prompted.
  4. The script writes the computed PIXELS_PER_MM value directly into config.py.
  5. Restart main.py – sizing will now be accurate.

Alternatively, you can just tell the script which produce to hold up and its actual
diameter, and it will calibrate using that fruit.
"""

import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
from picamera2 import Picamera2

from config import CAPTURE_PATH, PRODUCE_NAMES, YOLO_MODEL, YOLO_CONFIDENCE

DEBUG_PATH = CAPTURE_PATH.replace(".jpg", "_calibration.jpg")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py")


def capture_frame():
    cam = Picamera2()
    cfg = cam.create_still_configuration(main={"size": (1920, 1080), "format": "RGB888"})
    cam.configure(cfg)
    cam.start()
    frame = cam.capture_array()
    cam.stop()
    cam.close()
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    cv2.imwrite(CAPTURE_PATH, frame_bgr)
    print(f"  Captured: {CAPTURE_PATH}")
    return frame_bgr


def detect_with_yolo(frame_bgr, target_class=None):
    """Return (w_px, h_px) of the best YOLO detection, or None."""
    try:
        from ultralytics import YOLO
        model = YOLO(YOLO_MODEL)
        results = model(frame_bgr, conf=YOLO_CONFIDENCE, verbose=False)
        if not results or results[0].boxes is None:
            return None
        boxes = results[0].boxes
        names = results[0].names
        best, best_area = None, 0
        for box in boxes:
            cls_name = names.get(int(box.cls[0]), "")
            if target_class and cls_name.lower() != target_class.lower():
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            area = (x2 - x1) * (y2 - y1)
            print(f"  YOLO: {cls_name}  conf={float(box.conf[0]):.2f}  size={x2-x1}×{y2-y1}px")
            if area > best_area:
                best_area = area
                best = (x2 - x1, y2 - y1)
        return best
    except Exception as e:
        print(f"  YOLO error: {e}")
        return None


def detect_with_opencv(frame_bgr):
    """Return (w_px, h_px) of the best OpenCV contour, or None."""
    h, w = frame_bgr.shape[:2]
    frame_area = h * w
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    for inv in (False, True):
        flags = (cv2.THRESH_BINARY_INV if inv else cv2.THRESH_BINARY) + cv2.THRESH_OTSU
        _, thresh = cv2.threshold(blurred, 0, 255, flags)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = [c for c in contours
                      if 0.02 * frame_area <= cv2.contourArea(c) <= 0.90 * frame_area]
        if candidates:
            largest = max(candidates, key=cv2.contourArea)
            _, _, cw, ch = cv2.boundingRect(largest)
            print(f"  OpenCV contour: {cw}×{ch}px  area={cv2.contourArea(largest):.0f}px²")
            return (cw, ch)
    return None


def save_pixels_per_mm(value: float):
    """Overwrite PIXELS_PER_MM in config.py."""
    with open(CONFIG_PATH, "r") as f:
        content = f.read()
    # Replace the PIXELS_PER_MM line
    new_line = (
        f"PIXELS_PER_MM     = {value:.4f}  # Calibrated by calibrate.py\n"
        f"                          # Re-run calibrate.py if camera distance changes"
    )
    content = re.sub(
        r"PIXELS_PER_MM\s*=.*(?:\n\s*#.*)?",
        new_line,
        content,
        count=1,
    )
    with open(CONFIG_PATH, "w") as f:
        f.write(content)
    print(f"\n  ✓ Saved PIXELS_PER_MM = {value:.4f} to config.py")


def main():
    print("=" * 55)
    print("  PIXELS_PER_MM Calibration")
    print("=" * 55)
    print()
    print("Place your calibration object under the camera")
    print("(same position / height as fruit on the belt).")
    print()

    # Ask for YOLO target class
    print("Produce choices for auto-detection:")
    for i, name in enumerate(PRODUCE_NAMES):
        print(f"  {i+1}. {name}")
    print("  0. Other (use OpenCV / manual px input)")
    choice = input("\nEnter number (or 0 for manual): ").strip()

    target_class = None
    if choice.isdigit() and int(choice) >= 1:
        idx = int(choice) - 1
        if 0 <= idx < len(PRODUCE_NAMES):
            from config import YOLO_CLASS_MAP
            target_class = YOLO_CLASS_MAP.get(PRODUCE_NAMES[idx])

    input("\nPress ENTER when object is in position…")
    print("Capturing…")
    frame = capture_frame()

    # Detect
    result = detect_with_yolo(frame, target_class)
    if not result:
        print("  YOLO found nothing – trying OpenCV…")
        result = detect_with_opencv(frame)
    if not result:
        px = int(input("  No auto-detection. Enter detected width in pixels manually: "))
        result = (px, px)

    w_px, h_px = result
    size_px = max(w_px, h_px)
    print(f"\n  Detected size: {size_px} px  (w={w_px} h={h_px})")

    actual_mm = float(input("  Enter the ACTUAL width/diameter of the object in mm: "))
    ppm = size_px / actual_mm
    print(f"\n  PIXELS_PER_MM = {size_px} px ÷ {actual_mm} mm = {ppm:.4f}")

    save_pixels_per_mm(ppm)
    print("\nDone! Restart main.py to use the new calibration.")


if __name__ == "__main__":
    main()

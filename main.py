"""
main.py – Fruit Classification System: main event loop.

Flow:
    startup → init all modules → start OLED idle loop
    loop:
      1. Non-blocking keypad poll
         C + digit → select produce → show on OLED for 3 s
      2. Wait for IR sensor to detect a fruit (blocking)
      3. Capture image + measure size (camera)
      4. Classify size (classifier)
      5. Determine relay + delay, schedule non-blocking relay pulse
      6. Show result on OLED for 3 s
      7. Repeat

Run as root (or add user to gpio group):
    python main.py
"""

import sys
import time
import signal
import logging


from config       import (
    PRODUCE_NAMES,
    RELAY_DELAYS,
    RELAY_PULSE_DURATION,
    SIZE_TO_RELAY,
    DEFAULT_SIZE_MM,
)
from camera           import Camera
from classifier       import classify_info
from ir_sensor        import IRSensor
from keypad           import Keypad
from oled_display     import OLEDDisplay
from relay_controller import RelayController

# ─── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ─── Graceful shutdown ────────────────────────────────────────────────────────
_RUNNING = True

def _shutdown(sig, frame):
    global _RUNNING
    log.info("Shutdown signal received – cleaning up …")
    _RUNNING = False

signal.signal(signal.SIGINT,  _shutdown)
signal.signal(signal.SIGTERM, _shutdown)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():

    log.info("Initialising hardware modules …")
    camera  = Camera()
    ir      = IRSensor()
    keypad  = Keypad()
    relays  = RelayController()
    display = OLEDDisplay()

    # Default produce: Apple (index 0)
    selected_produce: int = 0
    log.info(f"Default produce: {PRODUCE_NAMES[selected_produce]}")

    display.start()
    log.info("System ready – waiting for fruit …")

    try:
        while _RUNNING:
            # ── 1. Non-blocking keypad scan ──────────────────────────────────
            new_produce = keypad.poll_produce_select()
            if new_produce is not None:
                selected_produce = new_produce
                log.info(f"Produce changed to: {PRODUCE_NAMES[selected_produce]}")
                display.show_produce_selected(
                    PRODUCE_NAMES[selected_produce], selected_produce
                )
                # Brief pause so operator sees the OLED update
                time.sleep(0.2)
                continue

            # ── 2. Wait for IR sensor (short timeout to keep keypad responsive)
            if not ir.is_triggered():
                time.sleep(0.05)
                continue

            log.info("IR trigger detected – capturing image …")

            # ── 3. Capture image + measure ───────────────────────────────────
            try:
                size_mm, img_path = camera.capture_and_measure(
                    produce_name=PRODUCE_NAMES[selected_produce]
                )
            except Exception as e:
                log.error(f"Camera error: {e}")
                continue

            log.info(f"Measured size: {size_mm} mm  (image: {img_path})")

            # Size 0.0 means the camera could not detect a fruit contour
            if size_mm == 0.0:
                if DEFAULT_SIZE_MM > 0:
                    size_mm = DEFAULT_SIZE_MM
                    log.warning(
                        f"Camera failed to detect fruit – using fallback size: "
                        f"{DEFAULT_SIZE_MM} mm. Reposition cameras to fix this."
                    )
                else:
                    log.warning(
                        "Camera returned 0.0 mm – fruit not detected. "
                        "Skipping relay (DEFAULT_SIZE_MM=0)."
                    )
                    time.sleep(1.0)
                    continue

            # ── 4. Classify ──────────────────────────────────────────────────
            info = classify_info(size_mm, selected_produce)
            category = info["category"]
            log.info(f"Classification: {info['produce_name']} → {category}")

            # ── 5. Schedule relay ────────────────────────────────────────────
            relay_index = SIZE_TO_RELAY.get(category)   # None for "unknown"
            relay_delay = RELAY_DELAYS.get(category, 0)

            if relay_index is not None:
                relay_num_1based = relay_index + 1
                log.info(
                    f"Scheduling Relay {relay_num_1based} in {relay_delay}s "
                    f"(pulse {RELAY_PULSE_DURATION}s)"
                )
                relays.schedule(relay_index, relay_delay, RELAY_PULSE_DURATION)
            else:
                relay_num_1based = None
                log.info("Unknown size – no relay fired")

            # ── 6. Update OLED ───────────────────────────────────────────────
            display.show_event(
                produce_name=info["produce_name"],
                category=category,
                relay_num=relay_num_1based,
            )

            # Brief cooldown so the same fruit isn't re-detected
            time.sleep(1.0)

    finally:
        log.info("Shutting down …")
        display.stop()
        relays.cleanup()
        ir.cleanup()
        keypad.cleanup()
        camera.close()
        log.info("Goodbye.")


if __name__ == "__main__":
    main()

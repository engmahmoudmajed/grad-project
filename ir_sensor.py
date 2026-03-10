"""
ir_sensor.py – IR obstacle sensor driver.

The sensor outputs LOW (0) when an object is detected.
GPIO BCM pin 26 is used (see config.py).

Usage:
    from ir_sensor import IRSensor
    sensor = IRSensor()
    sensor.wait_for_fruit()      # blocks until a fruit is detected
    sensor.cleanup()
"""

import time
import lgpio
from config import IR_SENSOR_PIN, IR_DEBOUNCE_SECS


class IRSensor:
    def __init__(self):
        self._chip = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_input(self._chip, IR_SENSOR_PIN, lgpio.SET_PULL_UP)
        self._last_trigger = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def is_triggered(self) -> bool:
        """Return True if an object is currently blocking the IR beam."""
        return lgpio.gpio_read(self._chip, IR_SENSOR_PIN) == 0

    def wait_for_fruit(self, poll_interval: float = 0.05) -> None:
        """
        Block until the sensor detects a fruit AND the debounce window has passed.

        poll_interval: seconds between GPIO reads (default 50 ms).
        """
        while True:
            if self.is_triggered():
                now = time.time()
                if now - self._last_trigger >= IR_DEBOUNCE_SECS:
                    self._last_trigger = now
                    return
            time.sleep(poll_interval)

    def cleanup(self) -> None:
        """Release the GPIO pin (call when the program exits)."""
        lgpio.gpiochip_close(self._chip)

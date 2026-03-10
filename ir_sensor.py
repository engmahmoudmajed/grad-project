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
import RPi.GPIO as GPIO
from config import IR_SENSOR_PIN, IR_DEBOUNCE_SECS


class IRSensor:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(IR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._last_trigger = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def is_triggered(self) -> bool:
        """Return True if an object is currently blocking the IR beam."""
        return GPIO.input(IR_SENSOR_PIN) == GPIO.LOW

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
        GPIO.cleanup(IR_SENSOR_PIN)

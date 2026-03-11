"""
relay_controller.py – GPIO relay control with timed pulses.

Supports both active-HIGH (Normally-Open) and active-LOW relay boards.
Set RELAY_ACTIVE_LOW in config.py:
  False = active-HIGH / Normally-Open  (GPIO HIGH → relay ON)  ← current setting
  True  = active-LOW  / Normally-Closed (GPIO LOW  → relay ON)

Usage:
    from relay_controller import RelayController
    relays = RelayController()
    relays.activate(relay_index=0, pulse_duration=5)          # blocking
    relays.schedule(relay_index=1, delay_secs=10, pulse_duration=5)  # non-blocking
    relays.cleanup()
"""

import time
import threading
import lgpio
from config import RELAY_PINS, RELAY_ACTIVE_LOW


class RelayController:
    def __init__(self):
        self._chip = lgpio.gpiochip_open(0)
        # Determine the electrical levels for ON / OFF
        self._on_level  = 0 if RELAY_ACTIVE_LOW else 1
        self._off_level = 1 if RELAY_ACTIVE_LOW else 0

        for pin in RELAY_PINS:
            lgpio.gpio_claim_output(self._chip, pin, self._off_level)  # start OFF

        self._threads: list[threading.Thread] = []

    # ── Public API ────────────────────────────────────────────────────────────

    def activate(self, relay_index: int, pulse_duration: float) -> None:
        """
        Immediately activate a relay for `pulse_duration` seconds (BLOCKING).

        relay_index: 0-based index into RELAY_PINS.
        """
        self._validate_index(relay_index)
        pin = RELAY_PINS[relay_index]
        try:
            lgpio.gpio_write(self._chip, pin, self._on_level)
            time.sleep(pulse_duration)
        finally:
            lgpio.gpio_write(self._chip, pin, self._off_level)

    def schedule(
        self,
        relay_index: int,
        delay_secs: float,
        pulse_duration: float,
    ) -> threading.Thread:
        """
        Schedule a relay activation in the future (NON-BLOCKING).

        A background thread sleeps `delay_secs` then calls `activate()`.
        Returns the Thread object so the caller can `.join()` if needed.
        """
        self._validate_index(relay_index)

        def _run():
            time.sleep(delay_secs)
            self.activate(relay_index, pulse_duration)

        t = threading.Thread(target=_run, daemon=True)
        self._threads.append(t)
        t.start()
        return t

    def all_off(self) -> None:
        """Force all relays OFF immediately (safety method)."""
        for pin in RELAY_PINS:
            lgpio.gpio_write(self._chip, pin, self._off_level)

    def cleanup(self) -> None:
        """Turn off relays and release GPIO pins."""
        self.all_off()
        lgpio.gpiochip_close(self._chip)

    # ── Private ───────────────────────────────────────────────────────────────

    def _validate_index(self, index: int) -> None:
        if index < 0 or index >= len(RELAY_PINS):
            raise ValueError(
                f"relay_index {index} out of range (0–{len(RELAY_PINS) - 1})"
            )

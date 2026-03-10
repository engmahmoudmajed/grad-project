"""
keypad.py – 4×4 matrix keypad driver.

Rows (GPIO outputs) are driven HIGH one at a time; columns (GPIO inputs with
pull-downs) are read to detect which key is pressed.

Key mapping (from config.KEYPAD_LAYOUT):
    1 2 3 A
    4 5 6 B
    7 8 9 C
    * 0 # D

Special combination:
    C + <digit>  → selects produce type (index = digit - 1, i.e. '1'→0, …, '9'→8)

Usage:
    from keypad import Keypad
    kp = Keypad()
    key = kp.get_key()          # non-blocking; returns char or None
    produce_idx = kp.poll_produce_select()  # returns int or None
    kp.cleanup()
"""

import time
import RPi.GPIO as GPIO
from config import KEYPAD_ROWS, KEYPAD_COLS, KEYPAD_LAYOUT


_DEBOUNCE_MS = 50   # milliseconds


class Keypad:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)

        for row_pin in KEYPAD_ROWS:
            GPIO.setup(row_pin, GPIO.OUT, initial=GPIO.LOW)

        for col_pin in KEYPAD_COLS:
            GPIO.setup(col_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        self._last_key: str | None = None
        self._last_press_time: float = 0.0
        self._pending_c: bool = False   # True when 'C' was the last unique key press

    # ── Public API ────────────────────────────────────────────────────────────

    def get_key(self) -> str | None:
        """
        Scan the keypad once and return the pressed key character,
        or None if no key is pressed.  Includes simple debounce.
        """
        for row_idx, row_pin in enumerate(KEYPAD_ROWS):
            GPIO.output(row_pin, GPIO.HIGH)
            for col_idx, col_pin in enumerate(KEYPAD_COLS):
                if GPIO.input(col_pin) == GPIO.HIGH:
                    GPIO.output(row_pin, GPIO.LOW)
                    key = KEYPAD_LAYOUT[row_idx][col_idx]
                    now = time.time()
                    # Debounce: ignore repeated reporting of the same key
                    if key == self._last_key and (now - self._last_press_time) < (_DEBOUNCE_MS / 1000):
                        return None
                    self._last_key = key
                    self._last_press_time = now
                    return key
            GPIO.output(row_pin, GPIO.LOW)

        # No key pressed – reset tracking when all keys released
        self._last_key = None
        return None

    def poll_produce_select(self) -> int | None:
        """
        Non-blocking poll that implements the C+digit combination.

        - When 'C' is pressed, sets internal flag.
        - When a digit '1'–'9' follows, returns the 0-based produce index.
        - Any other key after 'C' cancels the sequence.
        - Returns None if no complete sequence detected.
        """
        key = self.get_key()
        if key is None:
            return None

        if key == "C":
            self._pending_c = True
            return None

        if self._pending_c:
            self._pending_c = False
            if key in "123456789":
                return int(key) - 1   # '1'→0, …, '9'→8

        return None

    def cleanup(self) -> None:
        """Release GPIO pins."""
        GPIO.cleanup(KEYPAD_ROWS + KEYPAD_COLS)

"""
oled_display.py – SH1106 OLED display driver.

Two modes:
  • Idle screen – rotates IP / CPU / RAM / Disk / Temperature every second
                  (adapted from Logic.md)
  • Event screen – shows produce name + size category for OLED_EVENT_SECS,
                   then automatically returns to idle

The display runs on a background thread so it never blocks the main loop.

Usage:
    from oled_display import OLEDDisplay
    display = OLEDDisplay()
    display.start()                        # begin idle loop
    display.show_event("Apple", "medium", relay_num=2)  # trigger event overlay
    display.stop()                         # clean shutdown
"""

import time
import threading
import subprocess

from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106

from config import (
    OLED_I2C_PORT,
    OLED_I2C_ADDRESS,
    OLED_WIDTH,
    OLED_HEIGHT,
    OLED_EVENT_SECS,
    FONT_PATH,
    ICON_FONT_PATH,
    FONT_SIZE,
    ICON_FONT_SIZE,
)


class OLEDDisplay:
    def __init__(self):
        serial = i2c(port=OLED_I2C_PORT, address=OLED_I2C_ADDRESS)
        self._device = sh1106(serial, width=OLED_WIDTH, height=OLED_HEIGHT, rotate=0)

        # Load fonts with graceful fallback
        try:
            self._font      = ImageFont.truetype(FONT_PATH,      FONT_SIZE)
            self._icon_font = ImageFont.truetype(ICON_FONT_PATH, ICON_FONT_SIZE)
        except IOError:
            self._font      = ImageFont.load_default()
            self._icon_font = ImageFont.load_default()

        self._stop_event    = threading.Event()
        self._event_lock    = threading.Lock()
        self._event_data: dict | None = None   # set by show_event()
        self._event_expires: float    = 0.0

        self._thread = threading.Thread(target=self._loop, daemon=True)

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background display thread."""
        self._thread.start()

    def stop(self) -> None:
        """Stop the display thread and clear the screen."""
        self._stop_event.set()
        self._thread.join(timeout=3)
        self._device.clear()

    def show_event(self, produce_name: str, category: str, relay_num: int | None) -> None:
        """
        Temporarily overlay an event message on the OLED.

        produce_name: e.g. "Apple"
        category:     "small" | "medium" | "big" | "unknown"
        relay_num:    1-based relay number, or None if no relay fires
        """
        with self._event_lock:
            self._event_data    = {
                "produce": produce_name,
                "category": category,
                "relay": relay_num,
            }
            self._event_expires = time.time() + OLED_EVENT_SECS

    def show_produce_selected(self, produce_name: str, produce_num: int) -> None:
        """Show a 'produce selected' message (called from keypad handler)."""
        with self._event_lock:
            self._event_data    = {
                "produce": produce_name,
                "category": f"Mode #{produce_num + 1}",
                "relay": None,
            }
            self._event_expires = time.time() + OLED_EVENT_SECS

    # ── Background thread ─────────────────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            with self._event_lock:
                event  = self._event_data
                expires = self._event_expires

            if event and time.time() < expires:
                self._draw_event(event)
            else:
                with self._event_lock:
                    self._event_data = None
                self._draw_idle()

            time.sleep(1.0)

    # ── Drawing helpers ───────────────────────────────────────────────────────

    def _new_canvas(self):
        img  = Image.new("1", (self._device.width, self._device.height))
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, self._device.width, self._device.height), fill=0)
        return img, draw

    def _draw_idle(self) -> None:
        """Idle screen: IP / CPU / RAM / Disk / Temperature."""
        img, draw = self._new_canvas()
        x, top = 0, -2

        ip    = self._shell("hostname -I | cut -d' ' -f1 | head --bytes -1", "No IP")
        cpu   = self._shell("top -bn1 | grep load | awk '{printf \"%.2fLA\", $(NF-2)}'", "0.00")
        mem   = self._shell("free -m | awk 'NR==2{printf \"%.2f%%\", $3*100/$2 }'", "0%")
        disk  = self._shell("df -h | awk '$NF==\"/\"{printf \"%d/%dGB\", $3,$2}'", "0/0GB")
        temp  = self._shell(
            "cat /sys/class/thermal/thermal_zone*/temp | awk -v CONVFMT='%.1f' '{printf $1/1000}'",
            "0"
        )

        # Icons (LineAwesome glyph codes)
        draw.text((x,      top +  5), chr(62609), font=self._icon_font, fill=255)  # Thermometer
        draw.text((x + 65, top +  5), chr(62776), font=self._icon_font, fill=255)  # Memory Chip
        draw.text((x,      top + 25), chr(63426), font=self._icon_font, fill=255)  # HDD
        draw.text((x + 65, top + 25), chr(62171), font=self._icon_font, fill=255)  # CPU Chip
        draw.text((x,      top + 45), chr(61931), font=self._icon_font, fill=255)  # Wifi

        draw.text((x + 19, top +  5), f"{temp}\u00B0C", font=self._font, fill=255)
        draw.text((x + 87, top +  5), mem,               font=self._font, fill=255)
        draw.text((x + 19, top + 25), disk,              font=self._font, fill=255)
        draw.text((x + 87, top + 25), cpu,               font=self._font, fill=255)
        draw.text((x + 19, top + 45), ip,                font=self._font, fill=255)

        self._device.display(img)

    def _draw_event(self, event: dict) -> None:
        """Event screen: produce name, size category, relay info."""
        img, draw = self._new_canvas()

        produce  = event["produce"]
        category = event["category"]
        relay    = event["relay"]

        draw.text((0,  0), produce,  font=self._font, fill=255)
        draw.text((0, 18), category, font=self._font, fill=255)

        if relay:
            draw.text((0, 36), f"Relay {relay} -> ON", font=self._font, fill=255)
        else:
            draw.text((0, 36), "No relay fired", font=self._font, fill=255)

        self._device.display(img)

    @staticmethod
    def _shell(cmd: str, fallback: str) -> str:
        try:
            return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        except Exception:
            return fallback

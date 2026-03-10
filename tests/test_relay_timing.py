"""
test_relay_timing.py – Simulated relay timing tests.

Uses unittest.mock to mock RPi.GPIO and time.sleep so these tests run on any
machine (no Pi hardware required).

Run with:  python -m pytest tests/test_relay_timing.py -v
"""

import sys
import os
import types
import importlib
from unittest.mock import MagicMock, patch, call

# ─── Stub out RPi.GPIO before importing project modules ──────────────────────
gpio_mock = MagicMock()
gpio_mock.BCM = 11
gpio_mock.OUT = 0
gpio_mock.IN  = 1
gpio_mock.LOW  = 0
gpio_mock.HIGH = 1
gpio_mock.PUD_DOWN = 21
gpio_mock.PUD_UP   = 22

sys.modules["RPi"]       = MagicMock()
sys.modules["RPi.GPIO"]  = gpio_mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestRelayController:
    """Test relay activation logic (relays mocked)."""

    def _make_controller(self):
        # Import fresh so mocks apply
        if "relay_controller" in sys.modules:
            del sys.modules["relay_controller"]
        from relay_controller import RelayController
        return RelayController()

    @patch("time.sleep")
    def test_activate_turns_on_then_off(self, mock_sleep):
        ctrl = self._make_controller()
        ctrl.activate(relay_index=0, pulse_duration=5)
        # Should have slept for exactly pulse_duration
        mock_sleep.assert_called_with(5)

    @patch("time.sleep")
    def test_activate_wrong_index_raises(self, mock_sleep):
        ctrl = self._make_controller()
        with pytest.raises(ValueError):
            ctrl.activate(relay_index=10, pulse_duration=5)

    @patch("time.sleep")
    def test_schedule_returns_thread(self, mock_sleep):
        import threading
        ctrl = self._make_controller()
        t = ctrl.schedule(relay_index=1, delay_secs=0, pulse_duration=1)
        t.join(timeout=2)
        assert isinstance(t, threading.Thread)

    @patch("time.sleep")
    def test_all_off_called_on_cleanup(self, mock_sleep):
        ctrl = self._make_controller()
        ctrl.all_off()   # should not raise


class TestSizeToRelayMapping:
    """Verify the SIZE_TO_RELAY and RELAY_DELAYS from config match the spec."""

    def test_small_maps_to_relay_0(self):
        from config import SIZE_TO_RELAY
        assert SIZE_TO_RELAY["small"] == 0

    def test_medium_maps_to_relay_1(self):
        from config import SIZE_TO_RELAY
        assert SIZE_TO_RELAY["medium"] == 1

    def test_big_maps_to_relay_2(self):
        from config import SIZE_TO_RELAY
        assert SIZE_TO_RELAY["big"] == 2

    def test_delays_match_spec(self):
        from config import RELAY_DELAYS
        assert RELAY_DELAYS["small"]  == 5
        assert RELAY_DELAYS["medium"] == 10
        assert RELAY_DELAYS["big"]    == 15

    def test_pulse_duration(self):
        from config import RELAY_PULSE_DURATION
        assert RELAY_PULSE_DURATION == 5

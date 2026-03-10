"""
test_classifier.py – Unit tests for the size classifier.

These tests run on any machine (no Raspberry Pi / GPIO needed).
Run with:  python -m pytest tests/test_classifier.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from classifier import classify_size, classify_info
from config import PRODUCE_NAMES, PRODUCE_SIZES_MM


# ─── Helpers ──────────────────────────────────────────────────────────────────

def midpoint(lo: int, hi: int) -> float:
    return (lo + hi) / 2.0


# ─── Basic classification for every produce × every size band ─────────────────

class TestClassifySize:
    @pytest.mark.parametrize("produce_index", range(len(PRODUCE_SIZES_MM)))
    def test_small_midpoint(self, produce_index):
        lo, hi = PRODUCE_SIZES_MM[produce_index][0]
        assert classify_size(midpoint(lo, hi), produce_index) == "small"

    @pytest.mark.parametrize("produce_index", range(len(PRODUCE_SIZES_MM)))
    def test_medium_midpoint(self, produce_index):
        lo, hi = PRODUCE_SIZES_MM[produce_index][1]
        assert classify_size(midpoint(lo, hi), produce_index) == "medium"

    @pytest.mark.parametrize("produce_index", range(len(PRODUCE_SIZES_MM)))
    def test_big_midpoint(self, produce_index):
        lo, hi = PRODUCE_SIZES_MM[produce_index][2]
        assert classify_size(midpoint(lo, hi), produce_index) == "big"

    # Boundary values
    @pytest.mark.parametrize("produce_index", range(len(PRODUCE_SIZES_MM)))
    def test_boundary_small_min(self, produce_index):
        lo, _ = PRODUCE_SIZES_MM[produce_index][0]
        assert classify_size(lo, produce_index) == "small"

    @pytest.mark.parametrize("produce_index", range(len(PRODUCE_SIZES_MM)))
    def test_boundary_big_max(self, produce_index):
        _, hi = PRODUCE_SIZES_MM[produce_index][2]
        assert classify_size(hi, produce_index) == "big"

    # Values outside all bands → unknown
    @pytest.mark.parametrize("produce_index", range(len(PRODUCE_SIZES_MM)))
    def test_too_small_is_unknown(self, produce_index):
        lo = PRODUCE_SIZES_MM[produce_index][0][0]
        assert classify_size(lo - 1, produce_index) == "unknown"

    @pytest.mark.parametrize("produce_index", range(len(PRODUCE_SIZES_MM)))
    def test_too_big_is_unknown(self, produce_index):
        hi = PRODUCE_SIZES_MM[produce_index][2][1]
        assert classify_size(hi + 1, produce_index) == "unknown"

    def test_zero_size_is_unknown(self):
        assert classify_size(0.0, 0) == "unknown"

    def test_invalid_produce_index_raises(self):
        with pytest.raises(ValueError):
            classify_size(60.0, 99)

    def test_negative_produce_index_raises(self):
        with pytest.raises(ValueError):
            classify_size(60.0, -1)


# ─── classify_info dict structure ─────────────────────────────────────────────

class TestClassifyInfo:
    def test_returns_dict_with_expected_keys(self):
        info = classify_info(72.0, 0)   # Apple medium
        assert set(info.keys()) == {"produce_name", "size_mm", "category"}

    def test_produce_name_matches_config(self):
        for idx, name in enumerate(PRODUCE_NAMES):
            info = classify_info(PRODUCE_SIZES_MM[idx][0][0], idx)
            assert info["produce_name"] == name

    def test_size_mm_is_rounded(self):
        info = classify_info(72.123456, 0)
        assert info["size_mm"] == round(72.123456, 1)

    def test_apple_medium(self):
        info = classify_info(72.0, 0)
        assert info["category"] == "medium"
        assert info["produce_name"] == "Apple"

    def test_banana_big(self):
        info = classify_info(170.0, 2)   # Banana big: 160–190 mm
        assert info["category"] == "big"

    def test_cucumber_small(self):
        info = classify_info(150.0, 7)   # Cucumber small: 120–180 mm
        assert info["category"] == "small"

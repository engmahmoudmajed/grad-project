"""
classifier.py – Classifies a measured fruit size into small / medium / big.

Usage:
    from classifier import classify_size
    result = classify_size(fruit_size_mm=72.5, produce_index=0)  # returns "medium"
"""

from config import PRODUCE_SIZES_MM, PRODUCE_NAMES


def classify_size(fruit_size_mm: float, produce_index: int) -> str:
    """
    Determine the size category of a fruit.

    Args:
        fruit_size_mm:  Measured dimension of the fruit in millimetres.
        produce_index:  Index into PRODUCE_SIZES_MM / PRODUCE_NAMES (0-based).

    Returns:
        "small", "medium", "big", or "unknown" if the measurement falls
        outside all defined bands.
    """
    if produce_index < 0 or produce_index >= len(PRODUCE_SIZES_MM):
        raise ValueError(
            f"produce_index {produce_index} out of range "
            f"(0–{len(PRODUCE_SIZES_MM) - 1})"
        )

    bands = PRODUCE_SIZES_MM[produce_index]
    size_labels = ["small", "medium", "big"]

    for label, (lo, hi) in zip(size_labels, bands):
        if lo <= fruit_size_mm <= hi:
            return label

    return "unknown"


def classify_info(fruit_size_mm: float, produce_index: int) -> dict:
    """
    Extended classification result, handy for display / logging.

    Returns a dict with keys:
        produce_name, size_mm, category
    """
    category = classify_size(fruit_size_mm, produce_index)
    return {
        "produce_name": PRODUCE_NAMES[produce_index],
        "size_mm":      round(fruit_size_mm, 1),
        "category":     category,
    }

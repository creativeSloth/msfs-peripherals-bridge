"""Pure numeric helpers for shaping axis values.

Kept free of any device or sim dependency so they are trivially testable.
"""

from __future__ import annotations

from ..models import CurveKind, Transform


def normalise(raw: int, raw_min: int, raw_max: int) -> float:
    """Map a raw axis reading to the symmetric range [-1.0, 1.0]."""
    if raw_max == raw_min:
        return 0.0
    frac = (raw - raw_min) / (raw_max - raw_min)
    return max(-1.0, min(1.0, frac * 2.0 - 1.0))


def apply_deadzone(value: float, deadzone: float) -> float:
    """Zero out small movements, then rescale so the edge stays at 1.0."""
    if deadzone <= 0.0:
        return value
    magnitude = abs(value)
    if magnitude <= deadzone:
        return 0.0
    sign = 1.0 if value >= 0 else -1.0
    return sign * (magnitude - deadzone) / (1.0 - deadzone)


def apply_curve(value: float, curve: CurveKind, expo: float) -> float:
    """Apply a response curve to a value in [-1, 1], preserving its sign."""
    sign = 1.0 if value >= 0 else -1.0
    magnitude = abs(value)
    if curve is CurveKind.SQUARED:
        magnitude = magnitude * magnitude
    elif curve is CurveKind.EXPO:
        # Blend between linear and cubic by the expo strength.
        magnitude = (1.0 - expo) * magnitude + expo * magnitude**3
    return sign * magnitude


def rescale(value: float, out_min: float, out_max: float) -> float:
    """Map a value in [-1, 1] onto [out_min, out_max]."""
    frac = (value + 1.0) / 2.0
    return out_min + frac * (out_max - out_min)


def shape_axis(raw: int, raw_min: int, raw_max: int, transform: Transform) -> float:
    """Run the full raw -> output pipeline for one axis sample."""
    value = normalise(raw, raw_min, raw_max)
    value = apply_deadzone(value, transform.deadzone)
    value = apply_curve(value, transform.curve, transform.expo)
    if transform.invert:
        value = -value
    return rescale(value, transform.out_min, transform.out_max)

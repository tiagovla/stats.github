"""Weekly contribution totals and waveform sample coordinates."""

from __future__ import annotations

from math import isfinite
from typing import Iterable

from .layout import StatsLayout


def weekly_totals(layout: StatsLayout) -> tuple[int, ...]:
    """Return exact contribution sums in the calendar's original week order."""
    return tuple(week.total for week in layout.weeks)


def waveform_y(values: Iterable[int | float], top: float, bottom: float) -> tuple[float, ...]:
    """Map nonnegative samples into a vertical range; an all-zero series sits at bottom."""
    samples = tuple(values)
    if not isfinite(top) or not isfinite(bottom) or bottom < top:
        raise ValueError("waveform bounds must be finite and bottom must not be above top")
    if any(not isfinite(value) or value < 0 for value in samples):
        raise ValueError("waveform values must be finite and nonnegative")
    peak = max(samples, default=0)
    if peak == 0:
        return tuple(float(bottom) for _ in samples)
    height = bottom - top
    return tuple(float(bottom - value / peak * height) for value in samples)

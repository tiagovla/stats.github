"""Build a repeatable weekly scan and hold timeline."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .layout import StatsLayout, StatsWeek


@dataclass(frozen=True)
class AnimationStep:
    week: StatsWeek
    at_seconds: float


@dataclass(frozen=True)
class AnimationSchedule:
    steps: tuple[AnimationStep, ...]
    duration_seconds: float
    scan_duration_seconds: float
    hold_seconds: float

    @property
    def active_seconds(self) -> float:
        return self.scan_duration_seconds

    @property
    def park_at_seconds(self) -> float:
        return self.scan_duration_seconds if self.steps else 0.0


def build_schedule(
    layout: StatsLayout,
    duration_seconds: float = 20.0,
    hold_fraction: float = 0.25,
) -> AnimationSchedule:
    """Place one sample per week during the scan, then hold the completed scan."""
    if not isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    if not isfinite(hold_fraction) or not 0 <= hold_fraction < 1:
        raise ValueError("hold_fraction must be in [0, 1)")

    hold_seconds = duration_seconds * hold_fraction
    scan_duration = duration_seconds - hold_seconds
    weeks = layout.weeks
    if not weeks:
        return AnimationSchedule((), duration_seconds, scan_duration, hold_seconds)
    interval = scan_duration / (len(weeks) - 1) if len(weeks) > 1 else 0
    steps = tuple(AnimationStep(week, index * interval) for index, week in enumerate(weeks))
    return AnimationSchedule(steps, duration_seconds, scan_duration, hold_seconds)

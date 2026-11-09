"""Parse GitHub contribution calendars without losing week positions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


@dataclass(frozen=True)
class StatsDay:
    date: date
    week: int
    weekday: int  # Sunday=0 through Saturday=6
    count: int
    level: int


@dataclass(frozen=True)
class StatsWeek:
    index: int
    days: tuple[StatsDay | None, ...]  # Sunday through Saturday

    @property
    def total(self) -> int:
        return sum(day.count for day in self.days if day is not None)


@dataclass(frozen=True)
class StatsLayout:
    weeks: tuple[StatsWeek, ...]

    @property
    def days(self) -> tuple[StatsDay, ...]:
        return tuple(day for week in self.weeks for day in week.days if day is not None)


def parse_contribution_calendar(calendar: dict[str, Any]) -> StatsLayout:
    """Parse GraphQL contributionCalendar data into Sunday-first week columns."""
    try:
        raw_weeks = calendar["weeks"]
    except (KeyError, TypeError) as exc:
        raise ValueError("calendar must contain weeks") from exc

    weeks = []
    for week_index, raw_week in enumerate(raw_weeks):
        slots: list[StatsDay | None] = [None] * 7
        try:
            raw_days = raw_week["contributionDays"]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"week {week_index} must contain contributionDays") from exc
        for raw_day in raw_days:
            try:
                day_date = date.fromisoformat(raw_day["date"])
                count = raw_day["contributionCount"]
                level = LEVELS[raw_day["contributionLevel"]]
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"invalid contribution day in week {week_index}") from exc
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise ValueError(f"invalid contributionCount in week {week_index}")
            weekday = (day_date.weekday() + 1) % 7
            if slots[weekday] is not None:
                raise ValueError(f"duplicate weekday in week {week_index}")
            slots[weekday] = StatsDay(day_date, week_index, weekday, count, level)
        weeks.append(StatsWeek(week_index, tuple(slots)))
    return StatsLayout(tuple(weeks))

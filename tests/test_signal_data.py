from datetime import date

import pytest

from github_stats.aggregation import waveform_y, weekly_totals
from github_stats.animation import build_schedule
from github_stats.layout import parse_contribution_calendar


def day(iso_date, count=0):
    return {
        "date": iso_date,
        "contributionCount": count,
        "contributionLevel": "FOURTH_QUARTILE" if count else "NONE",
    }


def test_layout_preserves_week_indices_and_partial_weekdays_and_sums_exactly():
    layout = parse_contribution_calendar({"weeks": [
        {"contributionDays": [day("2025-01-01", 2), day("2025-01-04", 5)]},
        {"contributionDays": [day("2025-01-05", 7)]},
    ]})

    assert [week.index for week in layout.weeks] == [0, 1]
    assert layout.weeks[0].days[0] is None
    assert layout.weeks[0].days[3].date == date(2025, 1, 1)
    assert layout.weeks[0].days[6].count == 5
    assert layout.weeks[0].days[6].level == 4
    assert layout.weeks[1].days[0].count == 7
    assert weekly_totals(layout) == (7, 7)


def test_waveform_y_maps_peak_to_top_and_all_zero_to_bottom():
    assert waveform_y((0, 2, 4), 10, 30) == (30.0, 20.0, 10.0)
    assert waveform_y((0, 0), 10, 30) == (30.0, 30.0)
    assert waveform_y((), 10, 30) == ()


def test_weekly_schedule_scans_then_holds_for_default_twenty_second_loop():
    layout = parse_contribution_calendar({"weeks": [
        {"contributionDays": [day("2025-01-01", 1)]},
        {"contributionDays": [day("2025-01-05", 2)]},
    ]})

    schedule = build_schedule(layout)

    assert [step.week.index for step in schedule.steps] == [0, 1]
    assert [step.at_seconds for step in schedule.steps] == [0, 15.0]
    assert schedule.duration_seconds == 20
    assert schedule.scan_duration_seconds == schedule.park_at_seconds == 15
    assert schedule.hold_seconds == 5


def test_single_week_is_sampled_at_scan_start():
    layout = parse_contribution_calendar({"weeks": [
        {"contributionDays": [day("2025-01-01", 1)]},
    ]})

    schedule = build_schedule(layout)

    assert [step.at_seconds for step in schedule.steps] == [0]


@pytest.mark.parametrize("duration", [0, -1, float("inf"), float("nan")])
def test_schedule_rejects_invalid_duration(duration):
    layout = parse_contribution_calendar({"weeks": []})
    with pytest.raises(ValueError):
        build_schedule(layout, duration_seconds=duration)


def test_waveform_rejects_negative_values_and_invalid_bounds():
    with pytest.raises(ValueError):
        waveform_y((1, -1), 0, 1)
    with pytest.raises(ValueError):
        waveform_y((1,), 2, 1)


def test_layout_rejects_unknown_contribution_level():
    with pytest.raises(ValueError, match="invalid contribution day"):
        parse_contribution_calendar({"weeks": [{"contributionDays": [{
            "date": "2025-01-01",
            "contributionCount": 1,
            "contributionLevel": "UNKNOWN",
        }]}]})

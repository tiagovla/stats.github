import xml.etree.ElementTree as ET

import pytest

from github_stats.activity_svg import render_activity_svg


NS = {"s": "http://www.w3.org/2000/svg"}
DATA = {"start": "2025-11-09", "end": "2026-11-09", "stars": 1234, "commits": 456, "pull_requests": 34, "issues": 12, "repositories": 8}
RANK = {"level": "A", "percentile": 92.5}


def test_activity_svg_contains_all_time_metrics_rank_dates_and_provenance():
    svg = render_activity_svg(DATA, RANK)
    root = ET.fromstring(svg)
    text = " ".join(root.itertext())
    desc = root.find("s:desc", NS).text

    assert root.attrib["role"] == "img"
    assert root.find("s:title", NS).text == "Developer activity overview"
    assert "DEVELOPER ACTIVITY / OVERVIEW" in text
    assert "1,234" in text and "456" in text and "34" in text and "12" in text and "8" in text
    assert "CURRENT STARS" in text and "TOTAL COMMITS" in text
    assert "TOTAL PULL" in text and "REQUESTS" in text
    assert "TOTAL ISSUES" in text and "OPENED" in text
    assert "TOTAL REPOS" in text and "CONTRIBUTED TO" in text
    assert "LAST 12 MONTHS" not in text
    assert "2025-11-09" in desc and "2026-11-09" in desc
    assert "Activity grade A" in desc
    assert "owned stars" in desc and "not a global ranking" in desc
    assert "all-time totals" in desc
    assert len(root.findall(".//s:path", NS)) == 5
    assert "https://" not in svg and "data:image" not in svg


def test_example_badge_light_theme_and_missing_rank():
    root = ET.fromstring(render_activity_svg(DATA, None, "light", example=True))
    text = " ".join(root.itertext())
    assert "Synthetic example data" in root.find("s:desc", NS).text
    assert "N/A" in text and "UNAVAILABLE" in text
    assert "required ranking inputs are missing" in root.find("s:desc", NS).text
    assert root.find("s:rect[@x='8']", NS).attrib["fill"] == "#f8fcfd"


def test_theme_and_rank_validation():
    with pytest.raises(ValueError, match="unknown theme"):
        render_activity_svg(DATA, RANK, "blue")
    with pytest.raises(ValueError, match="rank must contain"):
        render_activity_svg(DATA, {"level": "A", "percentile": 101})
    with pytest.raises(ValueError, match="nonnegative integer"):
        render_activity_svg({**DATA, "stars": -1}, RANK)

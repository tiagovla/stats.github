import xml.etree.ElementTree as ET

import pytest

from github_stats.animation import build_schedule
from github_stats.layout import parse_contribution_calendar
from github_stats.svg import render_svg


NS = {"s": "http://www.w3.org/2000/svg"}


def layout():
    return parse_contribution_calendar({"weeks": [
        {"contributionDays": [
            {"date": "2025-01-05", "contributionCount": 2, "contributionLevel": "FIRST_QUARTILE"},
            {"date": "2025-01-08", "contributionCount": 4, "contributionLevel": "FOURTH_QUARTILE"},
        ]},
        {"contributionDays": [
            {"date": "2025-01-12", "contributionCount": 1, "contributionLevel": "FIRST_QUARTILE"},
            {"date": "2025-01-18", "contributionCount": 3, "contributionLevel": "THIRD_QUARTILE"},
        ]},
    ]})


def test_svg_is_standalone_accessible_xml_with_weekly_wave_and_calendar():
    data = layout()
    rendered = render_svg(data, build_schedule(data))
    root = ET.fromstring(rendered)

    assert root.attrib["role"] == "img"
    assert root.find("s:title", NS).text == "Weekly contributions and daily activity"
    assert "2025-01-05: 2 contributions" in root.find("s:desc", NS).text
    assert "WEEKLY CONTRIBUTIONS" in "".join(root.itertext())
    assert "DAILY ACTIVITY" in "".join(root.itertext())
    assert root.find(".//s:path[@class='wave-line']", NS) is not None
    assert len(root.findall(".//s:rect[@class='cell']", NS)) == len(data.days)
    assert len(root.findall(".//s:rect[@class='cell-active']", NS)) == len(data.days)
    assert root.find(".//s:circle[@id='scan-dot']", NS) is not None
    assert root.find(".//s:clipPath[@id='scan-clip']", NS) is not None
    assert "@media(prefers-reduced-motion:reduce)" in root.find("s:style", NS).text
    assert "https://" not in rendered and "data:image" not in rendered


def test_wave_reveal_and_cursor_use_same_week_timeline():
    data = layout()
    rendered = render_svg(data, build_schedule(data, 12))
    style = ET.fromstring(rendered).find("s:style", NS).text

    assert "@keyframes scan-cursor" in style
    assert "@keyframes scan-width" in style
    assert "#scanner{animation:scan-cursor 12s linear infinite}" in style
    assert "#scan-clip rect{animation:scan-width 12s linear infinite}" in style
    assert "0.00000%{transform:translate(346.00px,0)}" in style
    assert "75.00000%{transform:translate(894.00px,0)}" in style


def test_light_theme_and_bad_theme():
    assert ET.fromstring(render_svg(layout(), build_schedule(layout()), "light")) is not None
    with pytest.raises(ValueError, match="unknown theme"):
        render_svg(layout(), build_schedule(layout()), "blue")

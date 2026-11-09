from github_stats.activity_svg import render_activity_svg
from github_stats.animation import build_schedule
from github_stats.language_svg import render_language_svg
from github_stats.layout import parse_contribution_calendar
from github_stats.svg import render_svg


THEMES = ("dark", "light", "github-dark", "github-light", "tokyodark")
ACTIVITY = {"start": "2025-01-01", "end": "2026-01-01", "stars": 5, "commits": 10,
            "pull_requests": 2, "issues": 1, "repositories": 3}


def test_all_renderers_accept_each_theme_and_emit_distinct_svg():
    layout = parse_contribution_calendar({"weeks": []})
    schedule = build_schedule(layout)
    renderers = (
        lambda theme: render_svg(layout, schedule, theme),
        lambda theme: render_language_svg([("Python", 100)], theme),
        lambda theme: render_activity_svg(ACTIVITY, {"level": "A", "percentile": 90}, theme),
    )

    for render in renderers:
        outputs = [render(theme) for theme in THEMES]
        assert len(set(outputs)) == len(THEMES)


def test_card_borders_match_across_modules():
    import xml.etree.ElementTree as ET
    from github_stats.animation import build_schedule
    from github_stats.layout import parse_contribution_calendar
    from github_stats.svg import render_svg
    from github_stats.language_svg import render_language_svg
    from github_stats.activity_svg import render_activity_svg

    calendar = parse_contribution_calendar({"weeks": []})
    activity = {"start": "2020-01-01", "end": "2026-01-01", "stars": 0, "commits": 0,
                "pull_requests": 0, "issues": 0, "repositories": 0}
    for theme in ("dark", "light", "github-dark", "github-light", "tokyodark"):
        cards = [render_svg(calendar, build_schedule(calendar), theme),
                 render_language_svg([], theme), render_activity_svg(activity, None, theme)]
        borders = [ET.fromstring(card).find("{http://www.w3.org/2000/svg}rect[@x='8']").attrib for card in cards]
        assert len({(b["stroke"], b["stroke-width"], b["rx"]) for b in borders}) == 1

"""Render a standalone GitHub developer activity overview as SVG."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET


SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)

PALETTES = {
    "dark": {"bg": "#020b16", "panel": "#07182a", "border": "#07303b", "text": "#c8e3f1", "muted": "#9bb8c5", "accent": "#00d7e6", "track": "#173841", "rule": "#00a99f", "icon": "#bfdced"},
    "light": {"bg": "#edf5f7", "panel": "#f8fcfd", "border": "#c8dfe4", "text": "#152d40", "muted": "#647e91", "accent": "#087f70", "track": "#dbe6ec", "rule": "#d7e2e9", "icon": "#087f70"},
}


def _el(parent, name, **attrs):
    return ET.SubElement(parent, f"{{{SVG}}}{name}", {key.replace("_", "-"): str(value) for key, value in attrs.items()})


def render_activity_svg(data, rank, theme="dark", example=False):
    """Render lifetime activity metrics and a percentile rank badge."""
    if theme not in PALETTES:
        raise ValueError(f"unknown theme {theme!r}; expected 'dark' or 'light'")
    colors = PALETTES[theme]
    metrics = (("CURRENT STARS", data["stars"], "star"),
               ("TOTAL COMMITS", data["commits"], "commit"),
               ("TOTAL PULL REQUESTS", data["pull_requests"], "pull"),
               ("TOTAL ISSUES OPENED", data["issues"], "issue"),
               ("TOTAL REPOSITORIES CONTRIBUTED TO", data["repositories"], "repo"))
    for key, value in ((name, value) for name, value, _ in metrics):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{key.lower()} must be a nonnegative integer")
    if rank is None:
        level, percentile = "N/A", 0
    else:
        level, percentile = rank["level"], rank["percentile"]
        if not isinstance(level, str) or not level.strip() or isinstance(percentile, bool) or not isinstance(percentile, (int, float)) or not math.isfinite(percentile) or not 0 <= percentile <= 100:
            raise ValueError("rank must contain a level and percentile from 0 to 100")

    width, height = 1200, 360
    root = ET.Element(f"{{{SVG}}}svg", {"width": str(width), "height": str(height), "viewBox": f"0 0 {width} {height}", "role": "img", "aria-labelledby": "title desc", "preserveAspectRatio": "xMidYMid meet"})
    _el(root, "title", id="title").text = "Developer activity overview"
    start, end = data["start"], data["end"]
    rank_text = "Rank unavailable because required ranking inputs are missing." if rank is None else f"Activity grade {level.strip().upper()}."
    stars_as_of = f" Stars observed as of {data['stars_as_of']}." if data.get("stars_as_of") else ""
    description = f"GitHub account created {start}; statistics are current as of {end}. {rank_text} " + "; ".join(f"{name.lower()}: {value:,}" for name, value, _ in metrics) + ". Commit, pull request, issue, and repository counts are all-time totals; stars are the current snapshot." + stars_as_of + " Rank estimates use GitHub activity inputs including commits, pull requests, issues, reviews, owned stars, and followers; adapted from github-stats-extended calculateRank at fe0684b3; this is not a global ranking."
    if example:
        description += " Synthetic example data."
    _el(root, "desc", id="desc").text = description
    _el(root, "style").text = f"svg{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}.text{{fill:{colors['text']}}}.muted{{fill:{colors['muted']}}}.accent{{fill:{colors['accent']}}}.rule{{stroke:{colors['rule']}}}.icon{{fill:none;stroke:{colors['icon']};stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}}.header{{font-weight:700}}@keyframes appear{{from{{opacity:0}}to{{opacity:1}}}}@keyframes draw{{from{{stroke-dasharray:0 1000}}}}.metric{{animation:appear .4s ease both;animation-delay:calc(var(--i) * .15s)}}.rank-arc{{animation:draw 1s ease both}}@media(prefers-reduced-motion:reduce){{.metric,.rank-arc{{animation:none!important}}}}"
    _el(root, "rect", x=8, y=8, width=width-16, height=height-16, rx=14, fill=colors["panel"], stroke=colors["border"], stroke_width=1)
    _el(root, "text", x=66, y=60, font_size=25, letter_spacing=.4, **{"class": "text header"}).text = "DEVELOPER ACTIVITY / OVERVIEW"

    # Rank ring.
    cx, cy, radius = 155, 194, 99
    circumference = 2 * math.pi * radius
    _el(root, "circle", cx=cx, cy=cy, r=radius, fill="none", stroke=colors["track"], **{"stroke-width": 8})
    _el(root, "circle", cx=cx, cy=cy, r=radius, fill="none", stroke=colors["accent"] if rank is not None else "none", **{"class": "rank-arc"}, stroke_width=8, stroke_dasharray=f"{circumference*(1-percentile/100):.2f} {circumference:.2f}", transform=f"rotate(-90 {cx} {cy})", **{"stroke-linecap": "round"})
    _el(root, "text", x=cx, y=cy+18, text_anchor="middle", font_size=65 if rank is not None else 32, font_weight=700, **{"class": "accent" if rank is not None else "text"}).text = level.strip().upper()
    _el(root, "text", x=cx, y=cy+48, text_anchor="middle", font_size=13, letter_spacing=1.1, **{"class": "text"}).text = "ACTIVITY GRADE" if rank is not None else "UNAVAILABLE"

    _el(root, "line", x1=280, x2=280, y1=94, y2=299, **{"class": "rule", "stroke-width": 1.5})
    x_positions = (370, 546, 722, 898, 1074)
    paths = {
        "star": "M12 2.5l2.9 6 6.6 1-4.8 4.7 1.1 6.6-5.8-3.1-5.8 3.1 1.1-6.6-4.8-4.7 6.6-1z",
        "commit": "M5 12h3m8 0h3M5 12a2 2 0 1 0-4 0 2 2 0 0 0 4 0zm9 0a2 2 0 1 0-4 0 2 2 0 0 0 4 0zm9 0a2 2 0 1 0-4 0 2 2 0 0 0 4 0z",
        "pull": "M6 19V5m0 0a2 2 0 1 0 0 .01M6 9c0 7 12 7 12 0V5m0 14a2 2 0 1 0 0 .01M18 5a2 2 0 1 0 0 .01",
        "issue": "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zm0 4v6m0 3v.1",
        "repo": "M4 4h11l5 5v11H4zM15 4v5h5M8 12l-2 2 2 2m8-4 2 2-2 2m-2-5-3 6",
    }
    for index, (x, (label, value, icon)) in enumerate(zip(x_positions, metrics)):
        if index:
            _el(root, "line", x1=x-88, x2=x-88, y1=94, y2=299, **{"class": "rule", "stroke-width": 1.5})
        metric = _el(root, "g", style=f"--i:{index}", **{"class": "metric"})
        _el(metric, "path", d=paths[icon], transform=f"translate({x-30} 98) scale(2.5)", **{"class": "icon", "stroke-width": "1.25"})
        _el(metric, "text", x=x, y=216, text_anchor="middle", font_size=42, font_weight=650, textLength=min(154, len(f"{value:,}") * 24), lengthAdjust="spacingAndGlyphs", **{"class": "accent"}).text = f"{value:,}"
        label_node = _el(metric, "text", x=x, y=248 if icon in ("pull", "issue", "repo") else 252, text_anchor="middle", font_size=14 if icon == "repo" else 16, letter_spacing=.3, **{"class": "text"})
        first, second = {
            "star": ("CURRENT STARS", None), "commit": ("TOTAL COMMITS", None),
            "pull": ("TOTAL PULL", "REQUESTS"), "issue": ("TOTAL ISSUES", "OPENED"),
            "repo": ("TOTAL REPOS", "CONTRIBUTED TO"),
        }[icon]
        label_node.text = first
        if second:
            _el(label_node, "tspan", x=x, dy=21).text = second
    return ET.tostring(root, encoding="unicode", xml_declaration=True)

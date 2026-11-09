"""Render a static GitHub language composition card as standalone SVG."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET


SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)

PALETTES = {
    "dark": {"bg": "#020b16", "panel": "#07182a", "track": "#00101b", "border": "#253b53", "grid": "#123142", "text": "#a9e2ed", "muted": "#75a9b8"},
    "light": {"bg": "#edf5f7", "panel": "#f8fcfd", "track": "#e1eeeb", "border": "#b3c9d2", "grid": "#d4e5e9", "text": "#17424b", "muted": "#66858d"},
}

# GitHub Linguist colors for common languages; unknown languages use a neutral tone.
LANGUAGE_COLORS = {
    "C": "#555555", "C#": "#178600", "C++": "#f34b7d", "CSS": "#663399",
    "Dart": "#00b4ab", "Go": "#00ADD8", "HTML": "#e34c26", "Java": "#b07219",
    "JavaScript": "#f1e05a", "Jupyter Notebook": "#DA5B0B", "Kotlin": "#A97BFF",
    "Lua": "#000080", "Makefile": "#427819", "PHP": "#4F5D95", "Python": "#3572A5",
    "R": "#198CE7", "Ruby": "#701516", "Rust": "#dea584", "Scala": "#c22d40",
    "Shell": "#89e051", "Swift": "#F05138", "TypeScript": "#3178c6", "Vue": "#41b883",
}


def _el(parent, name, **attrs):
    return ET.SubElement(parent, f"{{{SVG}}}{name}", {key.replace("_", "-"): str(value) for key, value in attrs.items()})


def _label(name: str, limit: int = 12) -> str:
    return name if len(name) <= limit else name[: limit - 1].rstrip() + "…"


def render_language_svg(languages, theme: str = "dark") -> str:
    """Return an accessible, static SVG for (language name, actual percent) pairs."""
    if theme not in PALETTES:
        raise ValueError(f"unknown theme {theme!r}; expected 'dark' or 'light'")
    rows = []
    for item in languages:
        try:
            name, percentage = item
        except (TypeError, ValueError) as exc:
            raise ValueError("languages must contain (name, percentage) pairs") from exc
        if not isinstance(name, str) or not name.strip():
            raise ValueError("language names must be non-empty strings")
        if isinstance(percentage, bool) or not isinstance(percentage, (int, float)) or not math.isfinite(percentage) or not 0 <= percentage <= 100:
            raise ValueError(f"invalid percentage for {name!r}; expected a finite value from 0 to 100")
        rows.append((name.strip(), float(percentage)))

    rows.sort(key=lambda row: (-row[1], row[0]))
    colors = PALETTES[theme]
    width, top, row_height = 960, 112, 38
    height = top + max(1, len(rows)) * row_height + 24
    label_x, bar_x, bar_width, pct_x = 66, 215, 635, 936
    root = ET.Element(f"{{{SVG}}}svg", {
        "width": str(width), "height": str(height), "viewBox": f"0 0 {width} {height}",
        "role": "img", "aria-labelledby": "title desc", "preserveAspectRatio": "xMidYMid meet",
    })
    _el(root, "title", id="title").text = "GitHub language composition"
    if rows:
        summary = "; ".join(f"{name}: {pct:g}%" for name, pct in rows)
        desc = f"Language share on a shared 0 to 100 percent scale. {summary}."
    else:
        desc = "No language data is available."
    _el(root, "desc", id="desc").text = desc
    _el(root, "rect", x=8, y=8, width=width-16, height=height-16, rx=14, fill=colors["panel"], stroke=colors["border"])
    style = _el(root, "style")
    style.text = """svg{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
@keyframes appear{from{opacity:0}to{opacity:1}}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.language-row{animation:appear .4s ease both;animation-delay:calc(var(--i) * .12s)}
.language-bar{transform-box:fill-box;transform-origin:left;animation:grow .7s ease both;animation-delay:calc(var(--i) * .12s)}
@media(prefers-reduced-motion:reduce){.language-row,.language-bar{animation:none!important}}"""
    _el(root, "text", x=32, y=47, font_size=23, font_weight=700, letter_spacing=1, fill=colors["text"]).text = "LANGUAGE CODE COMPOSITION"
    for tick in (0, 25, 50, 75, 100):
        x = bar_x + bar_width * tick / 100
        _el(root, "text", x=x, y=95, text_anchor="middle", font_size=15, fill=colors["text"]).text = f"{tick}%"
        _el(root, "line", x1=x, x2=x, y1=102, y2=top + max(1, len(rows)) * row_height - 5, stroke=colors["grid"], **{"stroke-width": "1"})
    if not rows:
        _el(root, "text", x=32, y=top+20, font_size=13, fill=colors["muted"]).text = "No language data available"
    for index, (name, percentage) in enumerate(rows):
        y = top + index * row_height
        row = _el(root, "g", style=f"--i:{index}", **{"class": "language-row"})
        color = LANGUAGE_COLORS.get(name, "#8b9aa8")
        _el(row, "rect", x=34, y=y+3, width=19, height=19, rx=4, fill=color)
        label = _el(row, "text", x=label_x, y=y+20, font_size=18, fill=colors["text"])
        _el(label, "title").text = name
        label.text = _label(name)
        _el(row, "rect", x=bar_x, y=y+3, width=bar_width, height=19, rx=8, fill=colors["track"])
        if percentage:
            fill_width = bar_width*percentage/100
            _el(row, "rect", x=bar_x, y=y+3, width=f"{fill_width:.3f}", height=19, rx=8, fill=color, **{"class": "language-bar"})
        else:
            fill_width = 0
        pct_label = "<0.1%" if 0 < percentage < 0.1 else f"{percentage:.1f}%"
        _el(row, "text", x=pct_x, y=y+20, text_anchor="end", font_size=18, fill=colors["text"]).text = pct_label
    return ET.tostring(root, encoding="unicode", xml_declaration=True)

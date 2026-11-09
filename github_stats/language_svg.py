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


def _label(name: str, limit: int = 27) -> str:
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
    width, top, row_height = 960, 82, 36
    height = top + max(1, len(rows)) * row_height + 22
    label_x, bar_x, bar_width, pct_x = 32, 300, 540, 930
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
    _el(root, "text", x=32, y=42, font_size=16, letter_spacing=2, fill=colors["text"]).text = "LANGUAGE CODE COMPOSITION"
    _el(root, "text", x=bar_x, y=65, font_size=9, fill=colors["muted"]).text = "0%"
    _el(root, "text", x=bar_x+bar_width, y=65, text_anchor="end", font_size=9, fill=colors["muted"]).text = "100%"
    if not rows:
        _el(root, "text", x=32, y=top+20, font_size=13, fill=colors["muted"]).text = "No language data available"
    for index, (name, percentage) in enumerate(rows):
        y = top + index * row_height
        row = _el(root, "g", style=f"--i:{index}", **{"class": "language-row"})
        _el(row, "line", x1=label_x, x2=930, y1=y+row_height-2, y2=y+row_height-2, stroke=colors["grid"], **{"stroke-width": ".6"})
        label = _el(row, "text", x=label_x, y=y+15, font_size=12, fill=colors["text"])
        _el(label, "title").text = name
        label.text = _label(name)
        _el(row, "rect", x=bar_x, y=y+3, width=bar_width, height=12, rx=6, fill=colors["track"])
        for tick in (25, 50, 75):
            _el(row, "line", x1=bar_x+bar_width*tick/100, x2=bar_x+bar_width*tick/100, y1=y+3, y2=y+15, stroke=colors["grid"], **{"stroke-width": ".6"})
        if percentage:
            fill_width = bar_width*percentage/100
            _el(row, "rect", x=bar_x, y=y+3, width=f"{fill_width:.3f}", height=12, rx=6, fill=LANGUAGE_COLORS.get(name, "#8b9aa8"), **{"class": "language-bar"})
        else:
            fill_width = 0
        pct_label = "<0.1%" if 0 < percentage < 0.1 else f"{percentage:.1f}%"
        inside = percentage >= 82
        _el(row, "text", x=(bar_x+fill_width-8 if inside else min(bar_x+fill_width+8, pct_x)), y=y+14, text_anchor=("end" if inside else "start"), font_size=10, fill=(colors["panel"] if inside else colors["text"])).text = pct_label
    return ET.tostring(root, encoding="unicode", xml_declaration=True)

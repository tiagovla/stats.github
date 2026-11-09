"""Render a self-contained weekly contribution stats dashboard as SVG."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

from .aggregation import weekly_totals, waveform_y
from .layout import StatsLayout


SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)

PALETTES = {
    "dark": {"bg": "#020b16", "panel": "#07182a", "inner": "#00101b", "bezel": "#253b53", "grid": "#07303b", "text": "#a9e2ed", "muted": "#75a9b8", "line": "#0df4f0", "area": "#00c5b2", "preview": "#285b6d", "cell": "#061e29", "levels": ("#06402f", "#07854d", "#00b95c", "#00f56d"), "amber": "#ffc34e"},
    "light": {"bg": "#edf5f7", "panel": "#f8fcfd", "inner": "#f3fafb", "bezel": "#b3c9d2", "grid": "#c8dfe4", "text": "#17424b", "muted": "#66858d", "line": "#008e9a", "area": "#00a99f", "preview": "#9dbdc5", "cell": "#e1eeeb", "levels": ("#d6ece2", "#8ad5ad", "#28b976", "#008d57"), "amber": "#be7410"},
}


def _el(parent, name, **attrs):
    return ET.SubElement(parent, f"{{{SVG}}}{name}", {key.replace("_", "-"): str(value) for key, value in attrs.items()})


def _path(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    return "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in points)


def _frames(name: str, points: list[tuple[float, str]]) -> str:
    return f"@keyframes {name}{{" + " ".join(f"{max(0,min(100,p)):.5f}%{{{v}}}" for p, v in points) + "}"


def render_svg(layout: StatsLayout, schedule, theme: str = "dark") -> str:
    """Return responsive, standalone SVG; schedule positions the shared scanner."""
    if theme not in PALETTES:
        raise ValueError(f"unknown theme {theme!r}; expected 'dark' or 'light'")
    colors = PALETTES[theme]
    width, height = 1200, 400
    left, right = 72, 1168
    plot_top, plot_bottom = 83, 207
    rows_top, row_pitch = 246, 15
    n = max(1, len(layout.weeks))
    step = (right - left) / n
    totals = weekly_totals(layout)
    ys = waveform_y(totals, plot_top, plot_bottom)
    xs = [left + (i + .5) * step for i in range(len(totals))]
    line = _path(list(zip(xs, ys)))
    area = (f"M {left} {plot_bottom} " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in zip(xs, ys)) + f" L {right} {plot_bottom} Z") if totals else f"M {left} {plot_bottom} H {right} Z"
    duration = float(schedule.duration_seconds)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("schedule duration must be finite and positive")

    root = ET.Element(f"{{{SVG}}}svg", {"width": str(width), "height": str(height), "viewBox": f"0 0 {width} {height}", "role": "img", "aria-labelledby": "title desc", "preserveAspectRatio": "xMidYMid meet"})
    _el(root, "title", id="title").text = "Weekly contributions and daily activity"
    summary = ", ".join(f"{day.date.isoformat()}: {day.count} contributions" for day in layout.days)
    _el(root, "desc", id="desc").text = (f"Weekly contribution totals and a Sunday through Saturday daily activity calendar for {len(layout.days)} days. " + summary) if summary else "An empty weekly contribution chart and daily activity calendar."
    defs = _el(root, "defs")
    shell = _el(defs, "linearGradient", id="shell", x1="0", y1="0", x2="0", y2="1")
    _el(shell, "stop", offset="0", **{"stop-color": colors["panel"]})
    _el(shell, "stop", offset="1", **{"stop-color": colors["bg"]})
    inset = _el(defs, "linearGradient", id="inset", x1="0", y1="0", x2="0", y2="1")
    _el(inset, "stop", offset="0", **{"stop-color": colors["inner"]})
    _el(inset, "stop", offset="1", **{"stop-color": colors["bg"]})
    bezel = _el(defs, "linearGradient", id="bezel", x1="0", y1="0", x2="0", y2="1")
    _el(bezel, "stop", offset="0", **{"stop-color": "#61758a"})
    _el(bezel, "stop", offset=".12", **{"stop-color": colors["bezel"]})
    _el(bezel, "stop", offset=".88", **{"stop-color": colors["bezel"]})
    _el(bezel, "stop", offset="1", **{"stop-color": "#0b192a"})
    clip = _el(defs, "clipPath", id="plot-clip")
    _el(clip, "rect", x=left, y=plot_top, width=right-left, height=plot_bottom-plot_top)
    scan_clip = _el(defs, "clipPath", id="scan-clip", clipPathUnits="userSpaceOnUse")
    _el(scan_clip, "rect", x=left, y=plot_top, width=right-left, height=rows_top+7*row_pitch-plot_top+2)

    style = _el(root, "style")
    css = [
        f"svg{{font-family:system-ui,sans-serif;background:{colors['bg']};color:{colors['text']}}}",
        f".panel{{fill:url(#shell);stroke:url(#bezel);stroke-width:1.4}}.inset{{fill:url(#inset);stroke:{colors['bezel']};stroke-width:1.1}}.header{{fill:url(#shell);stroke:{colors['bezel']};stroke-width:1}}.grid{{stroke:{colors['grid']};stroke-width:.8}}",
        f".text{{fill:{colors['text']}}}.muted{{fill:{colors['muted']}}}.wave-preview{{fill:none;stroke:{colors['preview']};stroke-width:1.6;stroke-linejoin:round;stroke-linecap:round}}",
        f".wave-area{{fill:{colors['area']};opacity:.16}}.wave-line{{fill:none;stroke:{colors['line']};stroke-width:2.3;stroke-linejoin:round;stroke-linecap:round}}",
        f".dot{{fill:{colors['line']};stroke:#d2ffff;stroke-width:1.4;filter:url(#glow)}}.cursor{{stroke:{colors['amber']};stroke-width:1.7;filter:url(#glow)}}.cell{{stroke:{colors['grid']};stroke-width:.6}}",
        ".preview-cursor{opacity:.55}.axis{stroke:#5596aa;stroke-width:1}.axis-tick{stroke:#5596aa;stroke-width:1}.bezel-highlight{stroke:#9aafc1;stroke-width:.6;opacity:.55}",
    ]
    glow = _el(defs, "filter", id="glow", x="-150%", y="-150%", width="400%", height="400%")
    _el(glow, "feGaussianBlur", stdDeviation="2.2", result="blur")
    merge = _el(glow, "feMerge")
    _el(merge, "feMergeNode", **{"in": "blur"})
    _el(merge, "feMergeNode", **{"in": "SourceGraphic"})

    _el(root, "rect", x=8, y=8, width=width-16, height=height-16, rx=14, fill=colors["panel"], stroke=colors["grid"], **{"stroke-width": "1"})
    _el(root, "text", x=28, y=37, font_size=16, letter_spacing=2, **{"class": "text"}).text = "WEEKLY CONTRIBUTIONS  /  DAILY ACTIVITY"
    _el(root, "text", x=width-30, y=37, text_anchor="end", font_size=10, letter_spacing=2, **{"class": "muted"}).text = "GITHUB STATS"
    _el(root, "text", x=left, y=70, font_size=12, letter_spacing=1.6, **{"class": "text"}).text = "WEEKLY CONTRIBUTIONS"
    _el(root, "text", x=left, y=234, font_size=12, letter_spacing=1.6, **{"class": "text"}).text = "DAILY ACTIVITY"

    maximum = max(totals, default=0)
    _el(root, "line", x1=left, x2=left, y1=plot_top, y2=plot_bottom, **{"class": "axis"})
    for tick in range(5):
        y = plot_bottom - (plot_bottom-plot_top)*tick/4
        _el(root, "line", x1=left, x2=right, y1=y, y2=y, **{"class":"grid"})
        _el(root, "line", x1=left-5, x2=left, y1=y, y2=y, **{"class": "axis-tick"})
        _el(root, "text", x=left-9, y=y+4, text_anchor="end", font_size=9, **{"class":"muted"}).text = str(round(maximum*tick/4))
    for i in range(n+1):
        x = left + i*step
        _el(root, "line", x1=x, x2=x, y1=plot_top, y2=plot_bottom, **{"class":"grid", "opacity":".6"})
    _el(root, "path", d=area, **{"class":"wave-area", "clip-path":"url(#plot-clip)"})
    _el(root, "path", d=line, **{"class":"wave-preview", "clip-path":"url(#plot-clip)"})
    # One shared animated clip reveals the waveform and its fill in sync with the calendar scanner.
    reveal = _el(root, "g", id="revealed-wave", **{"clip-path":"url(#scan-clip)"})
    _el(reveal, "path", d=area, **{"class":"wave-area"})
    _el(reveal, "path", d=line, **{"class":"wave-line"})

    weekday_names = ("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT")
    for weekday, label in enumerate(weekday_names):
        _el(root, "text", x=left-11, y=rows_top+weekday*row_pitch+9, text_anchor="end", font_size=9, **{"class":"muted"}).text = label
    level_colors = colors["levels"]
    for week in layout.weeks:
        cell = max(3, min(row_pitch - 3, step*.76))
        x = left + week.index*step + (step-cell)/2
        for weekday, day in enumerate(week.days):
            if day is None:
                continue
            cy = rows_top+weekday*row_pitch
            _el(root, "rect", x=x, y=cy, width=cell, height=cell, rx=1.7, fill=colors["cell"], **{"class":"cell"})
    calendar = _el(root, "g", **{"clip-path":"url(#scan-clip)"})
    for week in layout.weeks:
        cell = max(3, min(row_pitch - 3, step*.76))
        x = left + week.index*step + (step-cell)/2
        for weekday, day in enumerate(week.days):
            if day is None:
                continue
            level = day.level
            _el(calendar, "rect", x=x, y=rows_top+weekday*row_pitch, width=cell, height=cell, rx=1.7, fill=level_colors[max(0, min(level-1, 3))] if level else colors["cell"], **{"class":"cell-active"})

    # Keep a completed scan visible when an SVG viewer does not run CSS animations.
    _el(root, "line", x1=(xs[-1] if xs else left), x2=(xs[-1] if xs else left), y1=plot_top-18, y2=rows_top+7*row_pitch+2, **{"class":"cursor-static"})
    cursor = _el(root, "g", id="scanner", transform=f"translate({(xs[-1] if xs else left):.2f} 0)")
    _el(cursor, "rect", x=-step*.38, y=rows_top, width=step*.76, height=7*row_pitch-4, rx=2, fill=colors["amber"], opacity=".12")
    _el(cursor, "line", x1=0, x2=0, y1=plot_top-18, y2=rows_top+7*row_pitch+2, **{"class":"cursor"})
    dot = _el(root, "circle", id="scan-dot", cx=(xs[-1] if xs else left), cy=(ys[-1] if ys else plot_bottom), r=5.2, **{"class":"dot"})

    scan = list(schedule.steps)
    cursor_frames, reveal_frames, dot_frames = [], [], []
    for step_item in scan:
        i = step_item.week.index
        if i >= len(xs):
            continue
        percent = max(0, min(100, step_item.at_seconds/duration*100))
        cursor_frames.append((percent, f"transform:translate({xs[i]:.2f}px,0)"))
        reveal_frames.append((percent, f"width:{min(right-left,xs[i]-left+step*.38):.2f}px"))
        dot_frames.append((percent, f"cx:{xs[i]:.2f}px;cy:{ys[i]:.2f}px"))
    if scan and xs:
        first_x = xs[scan[0].week.index]
        last_x = xs[scan[-1].week.index]
        cursor_frames.insert(0, (0, f"transform:translate({first_x:.2f}px,0)"))
        reveal_frames.insert(0, (0, f"width:{min(right-left,first_x-left+step*.38):.2f}px"))
        dot_frames.insert(0, (0, f"cx:{first_x:.2f}px;cy:{ys[scan[0].week.index]:.2f}px"))
        cursor_frames.extend([(100, f"transform:translate({last_x:.2f}px,0)")])
        reveal_frames.extend([(100, f"width:{right-left}px")])
        dot_frames.append((100, f"cx:{last_x:.2f}px;cy:{ys[scan[-1].week.index]:.2f}px"))
        css.extend([_frames("scan-cursor", cursor_frames), _frames("scan-dot", dot_frames), f"#scanner{{animation:scan-cursor {duration:g}s linear infinite}}", f"#scan-dot{{animation:scan-dot {duration:g}s linear infinite}}", f"#scan-clip rect{{animation:scan-width {duration:g}s linear infinite}}"])
        width_frames = [(p, f"width:{v.split(':',1)[1][:-2]}px") for p,v in reveal_frames]
        css.append(_frames("scan-width", width_frames))
    axis_y = rows_top+7*row_pitch+8
    _el(root, "line", x1=left, x2=right, y1=axis_y, y2=axis_y, **{"class": "axis"})
    for i in range(n):
        x = left+(i+.5)*step
        _el(root, "line", x1=x, x2=x, y1=axis_y, y2=axis_y+5, **{"class": "axis-tick"})
        if i == 0 or (i+1) % 4 == 0 or i == n-1:
            _el(root, "text", x=x, y=axis_y+19, text_anchor="middle", font_size=9, **{"class":"muted"}).text = str(i+1)
    css.append(".cursor-static{stroke:" + colors["amber"] + ";stroke-width:1.7;opacity:.8}")
    css.append("@media(prefers-reduced-motion:no-preference){.cursor-static{display:none}}")
    css.append("@media(prefers-reduced-motion:reduce){#scanner,#scan-dot,#scan-clip rect{animation:none!important}}")
    style.text = "\n".join(css)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)

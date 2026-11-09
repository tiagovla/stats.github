"""Command line interface for generating the GitHub stats SVG set."""

import argparse
from datetime import date
import json
import math
from pathlib import Path

from .activity_data import fetch_activity
from .activity_rank import calculate_rank
from .activity_svg import render_activity_svg
from .animation import build_schedule
from .api import fetch_calendar
from .language_data import aggregate_languages, fetch_language_data
from .language_svg import render_language_svg
from .layout import parse_contribution_calendar
from .svg import render_svg


def _positive_duration(value):
    try:
        duration = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("duration must be a number") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise argparse.ArgumentTypeError("duration must be a finite positive number")
    return duration


def _fixture(path):
    """Read the three fixtures from a directory or beside a legacy calendar fixture."""
    directory = path if path.is_dir() else path.parent
    calendar_path = directory / "sample.json" if path.is_dir() else path
    return (
        json.loads(calendar_path.read_text(encoding="utf-8")),
        json.loads((directory / "languages.json").read_text(encoding="utf-8")),
        json.loads((directory / "activity.json").read_text(encoding="utf-8")),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render GitHub contribution, language, and activity SVGs.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--username", help="GitHub username")
    source.add_argument("--fixture", type=Path, help="fixture directory (or legacy contribution fixture file)")
    parser.add_argument("-o", "--output", type=Path, default=Path("."), help="output directory (default: current directory)")
    parser.add_argument("--duration", type=_positive_duration, default=20.0, help="stats animation duration in seconds")
    parser.add_argument("--theme", choices=("dark", "light"), default="dark", help="SVG color theme")
    parser.add_argument("--end-date", type=date.fromisoformat, help="activity reporting end date (YYYY-MM-DD, UTC)")
    parser.add_argument("--all-commits", action="store_true", help="use upstream all-commits activity rank mode")
    parser.add_argument("--include-private", action="store_true", help="include private data where available")
    args = parser.parse_args(argv)

    try:
        if args.fixture:
            if args.end_date or args.include_private:
                raise ValueError("--end-date and --include-private cannot be used with fixtures")
            calendar, languages, activity = _fixture(args.fixture)
        else:
            calendar = fetch_calendar(args.username)
            languages = fetch_language_data(args.username, include_private=args.include_private)
            activity = fetch_activity(args.username, end_date=args.end_date, all_commits=args.all_commits, include_private=args.include_private)

        layout = parse_contribution_calendar(calendar)
        stats_svg = render_svg(layout, build_schedule(layout, duration_seconds=args.duration), args.theme)
        summary = aggregate_languages(languages)
        total = sum(languages.values())
        rows = [(name, size * 100 / total) for name, size in summary.items()] if total else []
        language_svg = render_language_svg(rows, args.theme)
        inputs = activity.get("rank_inputs")
        if inputs is not None and not isinstance(inputs, dict):
            raise ValueError("rank_inputs must be an object or null")
        rank = None if inputs is None or any(inputs.get(key) is None for key in ("commits", "prs", "issues", "reviews", "repos", "stars", "followers")) else calculate_rank(all_commits=args.all_commits, **inputs)
        activity_svg = render_activity_svg(activity, rank, args.theme, example=bool(args.fixture))

        output = args.output.parent if args.output.suffix.lower() == ".svg" else args.output
        paths = {
            "stats.svg": args.output if args.output.suffix.lower() == ".svg" else output / "stats.svg",
            "languages.svg": output / "languages.svg",
            "activity.svg": output / "activity.svg",
        }
        output.mkdir(parents=True, exist_ok=True)
        for name, rendered in (("stats.svg", stats_svg), ("languages.svg", language_svg), ("activity.svg", activity_svg)):
            paths[name].write_text(rendered, encoding="utf-8")
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        parser.exit(1, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

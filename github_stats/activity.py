"""Command line interface for the developer activity overview."""

import argparse
from datetime import date
import json
from pathlib import Path

from .activity_data import fetch_activity
from .activity_rank import calculate_rank
from .activity_svg import render_activity_svg


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render a GitHub developer activity overview as SVG.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--username", help="GitHub username")
    source.add_argument("--fixture", type=Path, help="JSON activity fixture")
    parser.add_argument("-o", "--output", type=Path, default=Path("activity.svg"))
    parser.add_argument("--theme", choices=("dark", "light"), default="dark")
    parser.add_argument("--end-date", type=date.fromisoformat, help="inclusive reporting end date (YYYY-MM-DD, UTC)")
    parser.add_argument("--all-commits", action="store_true", help="use the upstream all-commits ranking mode")
    parser.add_argument("--include-private", action="store_true", help="include private activity where available")
    args = parser.parse_args(argv)
    try:
        if args.fixture:
            if args.end_date or args.include_private:
                raise ValueError("--end-date and --include-private cannot be used with a fixture")
            data = json.loads(args.fixture.read_text(encoding="utf-8"))
        else:
            data = fetch_activity(args.username, end_date=args.end_date, all_commits=args.all_commits, include_private=args.include_private)
        inputs = data.get("rank_inputs")
        if inputs is not None and not isinstance(inputs, dict):
            raise ValueError("rank_inputs must be an object or null")
        rank = None if inputs is None or any(inputs.get(key) is None for key in ("commits", "prs", "issues", "reviews", "repos", "stars", "followers")) else calculate_rank(all_commits=args.all_commits, **inputs)
        rendered = render_activity_svg(data, rank, args.theme, example=bool(args.fixture))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        parser.exit(1, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

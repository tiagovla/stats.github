"""Command line interface for rendering a user's language composition."""

import argparse
import json
from pathlib import Path

from .language_data import aggregate_languages, fetch_language_data
from .language_svg import render_language_svg


def _positive_int(value):
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("top must be a positive integer") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("top must be a positive integer")
    return number


def _fixture_languages(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or any(
        not isinstance(name, str) or not name.strip()
        or isinstance(size, bool) or not isinstance(size, int) or size < 0
        for name, size in data.items()
    ):
        raise ValueError("language fixture must be a JSON object mapping language names to nonnegative byte counts")
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render a GitHub user's language composition as an SVG.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--username", help="GitHub username")
    source.add_argument("--fixture", type=Path, help="JSON object mapping language names to byte counts")
    parser.add_argument("-o", "--output", type=Path, default=Path("languages.svg"), help="output SVG path")
    parser.add_argument("--theme", choices=("dark", "light"), default="dark", help="SVG color theme")
    parser.add_argument("--top", type=_positive_int, default=7, help="number of languages to show")
    parser.add_argument("--include", action="append", default=[], metavar="REPOSITORY", help="include only this repository (repeatable)")
    parser.add_argument("--exclude", action="append", default=[], metavar="REPOSITORY", help="exclude this repository (repeatable)")
    parser.add_argument("--exclude-archived", action="store_true", help="omit archived repositories")
    parser.add_argument("--include-private", action="store_true", help="include private repositories when the token allows it")
    args = parser.parse_args(argv)

    try:
        if args.fixture and (args.include or args.exclude or args.exclude_archived or args.include_private):
            raise ValueError("repository selection options cannot be used with a language fixture")
        languages = (
            _fixture_languages(args.fixture)
            if args.fixture
            else fetch_language_data(
                args.username,
                include_private=args.include_private,
                include_archived=not args.exclude_archived,
                include=args.include,
                exclude=args.exclude,
            )
        )
        summary = aggregate_languages(languages, top=args.top)
        total = sum(languages.values())
        rows = [(name, size * 100 / total) for name, size in summary.items()] if total else []
        rendered = render_language_svg(rows, args.theme)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

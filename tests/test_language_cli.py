import json

import pytest


def test_language_cli_renders_fixture_percentages(tmp_path, monkeypatch):
    from github_stats import languages as cli

    seen = {}
    monkeypatch.setattr(cli, "render_language_svg", lambda rows, theme: seen.update(rows=rows, theme=theme) or "<svg/>")
    output = tmp_path / "nested" / "languages.svg"

    assert cli.main(["--fixture", "fixtures/languages.json", "--theme", "light", "--top", "2", "-o", str(output)]) == 0
    assert seen["theme"] == "light"
    assert seen["rows"] == [("Python", pytest.approx(18400 * 100 / 46400)), ("TypeScript", pytest.approx(13200 * 100 / 46400))]
    assert output.read_text(encoding="utf-8") == "<svg/>"


def test_language_cli_passes_repository_filters_and_archive_option(tmp_path, monkeypatch):
    from github_stats import languages as cli

    calls = []
    monkeypatch.setattr(cli, "fetch_language_data", lambda *args, **kwargs: calls.append((args, kwargs)) or {"Python": 1})
    monkeypatch.setattr(cli, "render_language_svg", lambda rows, theme: "<svg/>")

    assert cli.main([
        "--username", "octocat", "--include", "repo-a", "--include", "repo-b",
        "--exclude", "repo-c", "--exclude-archived", "--include-private", "-o", str(tmp_path / "out.svg"),
    ]) == 0
    assert calls == [(("octocat",), {
        "include_private": True, "include_archived": False,
        "include": ["repo-a", "repo-b"], "exclude": ["repo-c"],
    })]


def test_language_cli_rejects_missing_source_and_nonpositive_top():
    from github_stats.languages import main

    with pytest.raises(SystemExit):
        main([])
    with pytest.raises(SystemExit):
        main(["--fixture", "fixtures/languages.json", "--top", "0"])


def test_language_fixture_rejects_invalid_byte_counts(tmp_path):
    from github_stats.languages import main

    fixture = tmp_path / "bad.json"
    fixture.write_text(json.dumps({"Python": -1}), encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["--fixture", str(fixture), "-o", str(tmp_path / "out.svg")])


def test_language_cli_rejects_repository_filters_with_fixture(tmp_path):
    from github_stats.languages import main

    with pytest.raises(SystemExit):
        main(["--fixture", "fixtures/languages.json", "--include", "repo-a", "-o", str(tmp_path / "out.svg")])


def test_language_cli_passes_empty_rows_for_zero_totals(tmp_path, monkeypatch):
    from github_stats import languages as cli

    seen = {}
    monkeypatch.setattr(cli, "fetch_language_data", lambda *args, **kwargs: {"Python": 0})
    monkeypatch.setattr(cli, "render_language_svg", lambda rows, theme: seen.update(rows=rows) or "<svg/>")

    cli.main(["--username", "octocat", "-o", str(tmp_path / "out.svg")])
    assert seen["rows"] == []

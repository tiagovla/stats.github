import pytest
import requests

from github_stats import api


class Response:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


def calendar_payload():
    calendar = {"weeks": []}
    return {"data": {"user": {"contributionsCollection": {"contributionCalendar": calendar}}}}


def test_fetch_calendar_uses_gh_token_and_returns_calendar(monkeypatch):
    calls = []
    monkeypatch.setenv("GH_TOKEN", "preferred")
    monkeypatch.setenv("GITHUB_TOKEN", "fallback")
    monkeypatch.setattr(api.requests, "post", lambda *args, **kwargs: calls.append((args, kwargs)) or Response(calendar_payload()))

    result = api.fetch_calendar("octocat")

    assert result == {"weeks": []}
    assert calls[0][1]["headers"]["Authorization"] == "Bearer preferred"
    assert calls[0][1]["json"]["variables"] == {"login": "octocat"}
    assert calls[0][1]["timeout"] == 20


def test_fetch_calendar_falls_back_to_github_token(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "fallback")
    monkeypatch.setattr(api.requests, "post", lambda *args, **kwargs: Response(calendar_payload()))

    assert api.fetch_calendar("octocat") == {"weeks": []}


def test_fetch_calendar_requires_token(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(ValueError, match="GH_TOKEN or GITHUB_TOKEN"):
        api.fetch_calendar("octocat")


def test_fetch_calendar_reports_graphql_errors(monkeypatch):
    monkeypatch.setattr(api.requests, "post", lambda *args, **kwargs: Response({"errors": [{"message": "bad query"}]}))

    with pytest.raises(RuntimeError, match="bad query"):
        api.fetch_calendar("octocat", "token")


def test_fetch_calendar_redacts_token_from_graphql_errors(monkeypatch):
    monkeypatch.setattr(api.requests, "post", lambda *args, **kwargs: Response({"errors": [{"message": "bad secret-token"}]}))

    with pytest.raises(RuntimeError, match=r"bad \[redacted\]") as exc_info:
        api.fetch_calendar("octocat", "secret-token")
    assert "secret-token" not in str(exc_info.value)


def test_fetch_calendar_reports_http_errors_without_leaking_token(monkeypatch):
    error = requests.ConnectionError("request failed with Bearer secret-token")
    monkeypatch.setattr(api.requests, "post", lambda *args, **kwargs: Response(error=error))

    with pytest.raises(RuntimeError, match="request failed") as exc_info:
        api.fetch_calendar("octocat", "secret-token")
    assert "secret-token" not in str(exc_info.value)


def test_fetch_calendar_explains_rate_limit(monkeypatch):
    response = Response(error=requests.HTTPError("limited"))
    response.status_code = 429
    response.error.response = response
    monkeypatch.setattr(api.requests, "post", lambda *args, **kwargs: response)

    with pytest.raises(RuntimeError, match="rate limits"):
        api.fetch_calendar("octocat", "token")


def test_cli_requires_exactly_one_data_source():
    from github_stats.__main__ import main

    with pytest.raises(SystemExit):
        main([])
    with pytest.raises(SystemExit):
        main(["--username", "octocat", "--fixture", "sample.json"])


def test_cli_rejects_nonpositive_duration():
    from github_stats.__main__ import main

    with pytest.raises(SystemExit):
        main(["--fixture", "sample.json", "--duration", "0"])


def test_cli_renders_fixture_with_light_theme_and_twenty_second_default(tmp_path, monkeypatch):
    from github_stats import __main__ as cli

    rendered = {}

    def render(layout, schedule, theme):
        rendered.update(duration=schedule.duration_seconds, theme=theme)
        return "<svg/>"

    monkeypatch.setattr(cli, "render_svg", render)
    output = tmp_path / "nested" / "stats.svg"

    assert cli.main(["--fixture", "fixtures/sample.json", "--theme", "light", "--output", str(output)]) == 0
    assert rendered == {"duration": 20.0, "theme": "light"}
    assert output.read_text(encoding="utf-8") == "<svg/>"


def test_unified_cli_generates_all_svgs_from_fixture_directory(tmp_path):
    from github_stats.__main__ import main

    output = tmp_path / "out"
    assert main(["--fixture", "fixtures", "--output", str(output)]) == 0
    assert {path.name for path in output.iterdir()} == {"stats.svg", "languages.svg", "activity.svg"}
    assert all("<svg" in path.read_text(encoding="utf-8") for path in output.iterdir())


def test_unified_cli_does_not_write_outputs_when_fetch_fails(tmp_path, monkeypatch):
    from github_stats import __main__ as cli

    monkeypatch.setattr(cli, "fetch_calendar", lambda username: {"weeks": []})
    monkeypatch.setattr(cli, "fetch_language_data", lambda username: {})
    monkeypatch.setattr(cli, "fetch_activity", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    output = tmp_path / "out"

    with pytest.raises(SystemExit):
        cli.main(["--username", "octocat", "--output", str(output)])
    assert not output.exists()


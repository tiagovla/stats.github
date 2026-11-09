import requests
import pytest

from github_stats import language_data as data


class Response:
    def __init__(self, payload, next_url=None, error=None):
        self.payload = payload
        self.links = {"next": {"url": next_url}} if next_url else {}
        self.error = error

    def raise_for_status(self):
        if self.error:
            self.error.response = self
            raise self.error

    def json(self):
        return self.payload


def repo(name, *, fork=False, archived=False, private=False, owner="octocat"):
    return {"name": name, "fork": fork, "archived": archived, "private": private, "owner": {"login": owner}}


def test_fetches_owned_repo_languages_across_pages_and_filters_defaults(monkeypatch):
    calls = []
    pages = {
        f"{data.API_URL}/users/octocat/repos?type=owner&per_page=100": Response(
            [repo("one"), repo("fork", fork=True), repo("old", archived=True)],
            f"{data.API_URL}/users/octocat/repos?page=2"
        ),
        f"{data.API_URL}/users/octocat/repos?page=2": Response([repo("two")]),
        f"{data.API_URL}/repos/octocat/one/languages": Response({"Python": 10, "C": 2}),
        f"{data.API_URL}/repos/octocat/old/languages": Response({"Python": 3}),
        f"{data.API_URL}/repos/octocat/two/languages": Response({"C": 5}),
    }
    monkeypatch.setattr(data.requests, "get", lambda url, **kwargs: calls.append((url, kwargs)) or pages[url])

    assert data.fetch_language_data("octocat") == {"Python": 13, "C": 7}
    assert calls[0][1]["timeout"] == 20
    assert all("Authorization" not in kwargs["headers"] for _, kwargs in calls)


def test_filters_forks_archives_and_repo_names(monkeypatch):
    calls = []
    monkeypatch.setattr(data.requests, "get", lambda url, **kwargs: calls.append(url) or Response(
        [repo("keep"), repo("fork", fork=True), repo("archived", archived=True), repo("skip")]
        if url.endswith("repos?type=owner&per_page=100") else {"Go": 4}
    ))

    assert data.fetch_language_data(
        "octocat", include_forks=True, include_archived=False, include={"keep", "archived"}, exclude={"archived"}
    ) == {"Go": 4}
    assert calls.count(f"{data.API_URL}/repos/octocat/keep/languages") == 1
    assert calls.count(f"{data.API_URL}/repos/octocat/fork/languages") == 0


def test_private_opt_in_checks_authenticated_user_and_includes_public_and_private(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        if url.endswith("/user"):
            return Response({"login": "OctoCat"})
        if "user/repos?" in url:
            return Response([repo("public"), repo("private", private=True)])
        return Response({"Rust": 7})
    monkeypatch.setattr(data.requests, "get", get)

    assert data.fetch_language_data("octocat", token="secret", include_private=True) == {"Rust": 14}
    assert calls[0][1]["headers"]["Authorization"] == "Bearer secret"
    assert "visibility=all" in calls[1][0]


def test_private_opt_in_requires_matching_identity_and_token(monkeypatch):
    monkeypatch.setattr(data.requests, "get", lambda *args, **kwargs: Response({"login": "someone-else"}))
    with pytest.raises(ValueError, match="authenticated GitHub user"):
        data.fetch_language_data("octocat", "secret", include_private=True)
    with pytest.raises(ValueError, match="GH_TOKEN or GITHUB_TOKEN"):
        data.fetch_language_data("octocat", include_private=True)


def test_token_environment_precedence_and_repo_include_exclude(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "preferred")
    monkeypatch.setenv("GITHUB_TOKEN", "fallback")
    calls = []
    monkeypatch.setattr(data.requests, "get", lambda url, **kwargs: calls.append((url, kwargs)) or (
        Response({"login": "octocat"}) if url.endswith("/user") else
        Response([repo("one"), repo("two")]) if "user/repos?" in url else Response({"Python": 9})
    ))
    assert data.fetch_language_data("octocat", include_private=True, include={"two"}, exclude={"one"}) == {"Python": 9}
    assert all(call[1]["headers"]["Authorization"] == "Bearer preferred" for call in calls)


def test_failure_does_not_return_partial_totals_and_does_not_leak_token(monkeypatch):
    responses = iter([Response([repo("one"), repo("two")]), Response({"Python": 4}),
                      Response(None, error=requests.ConnectionError("Bearer secret"))])
    monkeypatch.setattr(data.requests, "get", lambda *args, **kwargs: next(responses))
    with pytest.raises(RuntimeError, match="request failed") as exc_info:
        data.fetch_language_data("octocat", "secret")
    assert "secret" not in str(exc_info.value)


def test_rejects_unexpected_language_payload(monkeypatch):
    monkeypatch.setattr(data.requests, "get", lambda *args, **kwargs: Response(
        [repo("bad")] if "users/" in args[0] else {"Python": -1}
    ))
    with pytest.raises(RuntimeError, match="invalid repository language data"):
        data.fetch_language_data("octocat")


def test_never_sends_token_to_untrusted_pagination_url(monkeypatch):
    calls = []
    monkeypatch.setattr(data.requests, "get", lambda url, **kwargs: calls.append((url, kwargs)) or (
        Response([repo("one")], "https://evil.example/steal") if "/users/" in url else Response({"Go": 4})
    ))
    with pytest.raises(RuntimeError, match="unsafe pagination URL"):
        data.fetch_language_data("octocat", "secret")
    assert all(url.startswith(data.API_URL) for url, _ in calls)


def test_ignores_repositories_not_owned_by_requested_user_and_private_without_opt_in(monkeypatch):
    calls = []
    monkeypatch.setattr(data.requests, "get", lambda url, **kwargs: calls.append(url) or Response(
        [repo("other", owner="attacker"), repo("private", private=True), repo("public")]
        if "/users/" in url else {"Go": 4}
    ))
    assert data.fetch_language_data("octocat") == {"Go": 4}
    assert calls == [f"{data.API_URL}/users/octocat/repos?type=owner&per_page=100",
                     f"{data.API_URL}/repos/octocat/public/languages"]


def test_aggregation_keeps_top_seven_without_grouping():
    assert data.aggregate_languages({"Z": 1, "Python": 9, "C": 7, "Go": 6, "Rust": 5, "Java": 4, "Lua": 3}) == {
        "Python": 9, "C": 7, "Go": 6, "Rust": 5, "Java": 4, "Lua": 3, "Z": 1,
    }


def test_aggregation_preserves_real_other_and_validates_inputs():
    assert data.aggregate_languages({"Other": 20, "Python": 10, "C": 1}, top=1) == {
        "Other": 20,
    }
    with pytest.raises(ValueError):
        data.aggregate_languages({"Python": True})
    with pytest.raises(ValueError):
        data.aggregate_languages({}, top=-1)

from datetime import date, datetime, timezone

import pytest

from github_stats import activity_data as data


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def repo(identifier, *, private=False, fork=False):
    return {"id": identifier, "isPrivate": private, "isFork": fork}


def info(*, created="2020-05-01T12:00:00Z", years=(2024, 2025), owner_repos=(), more=False, cursor=None,
         viewer="octocat", private_access=0, private_owned=0):
    return {"data": {
        "viewer": {"login": viewer, "privateRepos": {"totalCount": private_access}},
        "user": {
            "createdAt": created,
            "rankData": {
                "contributionYears": list(years), "totalCommitContributions": 55,
                "totalPullRequestReviewContributions": 9, "hasAnyRestrictedContributions": False,
            },
            "pullRequests": {"totalCount": 21},
            "openIssues": {"totalCount": 7}, "closedIssues": {"totalCount": 6},
            "followers": {"totalCount": 8}, "privateOwned": {"totalCount": private_owned},
            "repositories": {
                "nodes": [{"stargazerCount": stars, "isFork": fork} for stars, fork in owner_repos],
                "pageInfo": {"hasNextPage": more, "endCursor": cursor}, "totalCount": 2,
            },
        },
    }}


def repo_range(*, commits=(), issues=(), prs=(), created=(), created_more=False, created_cursor=None):
    return {"data": {"user": {"contributionsCollection": {
        "hasAnyRestrictedContributions": False,
        "commitContributionsByRepository": [{"repository": item} for item in commits],
        "issueContributionsByRepository": [{"repository": item} for item in issues],
        "pullRequestContributionsByRepository": [{"repository": item} for item in prs],
        "repositoryContributions": {
            "nodes": [{"repository": item} for item in created],
            "pageInfo": {"hasNextPage": created_more, "endCursor": created_cursor},
        },
    }}}}


def test_fetches_all_time_counts_repos_and_fully_paginated_stars(monkeypatch):
    graph_calls, search_calls = [], []

    def post(url, **kwargs):
        variables = kwargs["json"]["variables"]
        query = kwargs["json"]["query"]
        graph_calls.append((query, variables))
        if "RepositoriesContributedTo" in query:
            if variables["createdAfter"]:
                return Response(repo_range(created=(repo("d"),)))
            if variables["from"].startswith("2024"):
                return Response(repo_range(commits=(repo("a"),), issues=(repo("b"),),
                                           created=(repo("a"),), created_more=True, created_cursor="created2"))
            return Response(repo_range(commits=(repo("b"), repo("c", fork=True))))
        if variables["after"] is None:
            return Response(info(owner_repos=((7, False), (100, True)), more=True, cursor="stars2"))
        return Response(info(owner_repos=((11, False),)))

    def get(url, **kwargs):
        search_calls.append((url, kwargs))
        query = kwargs["params"]["q"]
        count = 101 if url.endswith("/commits") else 6 if "is:pr" in query else 7
        return Response({"total_count": count, "incomplete_results": False})

    monkeypatch.setattr(data.requests, "post", post)
    monkeypatch.setattr(data.requests, "get", get)

    result = data.fetch_activity("octocat", "token", end_date=date(2025, 3, 1))

    assert result == {
        "start": "2020-05-01", "end": "2025-03-01", "stars_as_of": datetime.now(timezone.utc).date().isoformat(),
        "commits": 101, "pull_requests": 6, "issues": 7, "repositories": 4, "stars": 18,
        "rank_inputs": None,
    }
    assert [variables["from"][:4] for query, variables in graph_calls if "RepositoriesContributedTo" in query] == ["2024", "2024", "2025"]
    assert [variables["to"] for query, variables in graph_calls if "RepositoriesContributedTo" in query][-1] == "2025-03-01T23:59:59Z"
    assert graph_calls[1][1]["after"] == "stars2"
    assert graph_calls[3][1]["createdAfter"] == "created2"
    assert "author-date:2020-05-01..2025-03-01" in search_calls[0][1]["params"]["q"]
    assert "created:2020-05-01..2025-03-01 is:pr" in search_calls[1][1]["params"]["q"]
    assert all("Authorization" not in call[1]["headers"] for call in search_calls)


def test_rank_inputs_keep_current_upstream_window_and_all_commits_override(monkeypatch):
    today = datetime.now(timezone.utc).date()
    monkeypatch.setattr(data.requests, "post", lambda *args, **kwargs: Response(
        repo_range() if "RepositoriesContributedTo" in kwargs["json"]["query"] else info(created=f"{today.year - 1}-01-01T00:00:00Z", years=(today.year,), owner_repos=((4, False), (8, True)))
    ))

    def get(url, **kwargs):
        query = kwargs["params"]["q"]
        count = 999 if url.endswith("/commits") and query == "author:octocat" else 42 if url.endswith("/commits") else 0
        return Response({"total_count": count, "incomplete_results": False})

    monkeypatch.setattr(data.requests, "get", get)
    activity = data.fetch_activity("octocat", "token", end_date=today, all_commits=True)

    assert activity["rank_inputs"] == {
        "commits": 999, "prs": 21, "issues": 13, "reviews": 9,
        "repos": 2, "stars": 12, "followers": 8,
    }


def test_private_data_requires_matching_viewer_and_public_keeps_rank_unavailable(monkeypatch):
    monkeypatch.setattr(data.requests, "post", lambda *args, **kwargs: Response(info(viewer="other")))
    with pytest.raises(ValueError, match="private activity requires"):
        data.fetch_activity("octocat", "token", include_private=True)

    def post(_, **kwargs):
        if "RepositoriesContributedTo" in kwargs["json"]["query"]:
            return Response(repo_range())
        return Response(info(private_access=1))

    monkeypatch.setattr(data.requests, "post", post)
    monkeypatch.setattr(data.requests, "get", lambda *args, **kwargs: Response({"total_count": 0, "incomplete_results": False}))
    activity = data.fetch_activity("octocat", "token", end_date=date(2025, 3, 1))
    assert activity["rank_inputs"] is None
    assert activity["commits"] == activity["pull_requests"] == activity["issues"] == 0


def test_repository_range_splits_saturated_year_and_deduplicates(monkeypatch):
    calls = []

    def post(url, **kwargs):
        variables = kwargs["json"]["variables"]
        start, end = variables["from"], variables["to"]
        calls.append((start, end))
        if len(calls) == 1:
            repos = tuple(repo(str(index)) for index in range(100))
            return Response(repo_range(commits=repos))
        suffix = "left" if start.startswith("2024-01-01") else "right"
        return Response(repo_range(commits=(repo(suffix),)))

    monkeypatch.setattr(data.requests, "post", post)
    result_set = set()
    data._repository_range(
        "octocat", datetime(2024, 1, 1, tzinfo=timezone.utc),
        datetime(2024, 1, 2, 23, 59, 59, tzinfo=timezone.utc), False, "token", result_set,
    )

    assert result_set == {"left", "right"}
    assert len(calls) == 3


def test_repository_range_fails_when_single_day_is_saturated(monkeypatch):
    monkeypatch.setattr(data.requests, "post", lambda *args, **kwargs: Response(
        repo_range(commits=tuple(repo(str(index)) for index in range(100)))
    ))
    when = datetime(2024, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(RuntimeError, match="single day"):
        data._repository_range("octocat", when, when, False, "token", set())


def test_graphql_errors_redact_token(monkeypatch):
    monkeypatch.setattr(data.requests, "post", lambda *args, **kwargs: Response({"errors": [{"message": "bad secret"}]}))
    with pytest.raises(RuntimeError, match="bad \\[redacted\\]") as exc_info:
        data.fetch_activity("octocat", "secret")
    assert "secret" not in str(exc_info.value)

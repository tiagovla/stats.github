"""Fetch lifetime GitHub activity and the current upstream rank inputs."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import os
import re

import requests


API_URL = "https://api.github.com"
GRAPHQL_URL = f"{API_URL}/graphql"
REPOSITORY_LIMIT = 100

_INFO_QUERY = """
query Activity($login: String!, $privacy: RepositoryPrivacy, $after: String) {
  viewer { login privateRepos: repositories(first: 1, privacy: PRIVATE, ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]) { totalCount } }
  user(login: $login) {
    createdAt
    rankData: contributionsCollection {
      contributionYears totalCommitContributions totalPullRequestReviewContributions
      hasAnyRestrictedContributions
    }
    pullRequests(first: 1) { totalCount }
    openIssues: issues(states: OPEN) { totalCount }
    closedIssues: issues(states: CLOSED) { totalCount }
    followers { totalCount }
    privateOwned: repositories(first: 1, ownerAffiliations: OWNER, privacy: PRIVATE) { totalCount }
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, privacy: $privacy) {
      nodes { stargazerCount isFork }
      pageInfo { hasNextPage endCursor }
      totalCount
    }
  }
}
"""
_REPOS_QUERY = """
query RepositoriesContributedTo($login: String!, $from: DateTime!, $to: DateTime!, $createdAfter: String) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      hasAnyRestrictedContributions
      commitContributionsByRepository(maxRepositories: 100) { repository { id isPrivate isFork } }
      issueContributionsByRepository(maxRepositories: 100) { repository { id isPrivate isFork } }
      pullRequestContributionsByRepository(maxRepositories: 100) { repository { id isPrivate isFork } }
      repositoryContributions(first: 100, after: $createdAfter) {
        nodes { repository { id isPrivate isFork } }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""


def _token(token):
    return token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")


def _post(query, variables, token):
    try:
        response = requests.post(
            GRAPHQL_URL, json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {token}"}, timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (403, 429):
            raise RuntimeError(f"GitHub API returned HTTP {status}; check token permissions or rate limits") from exc
        raise RuntimeError(f"GitHub API request failed{f' (HTTP {status})' if status else ''}") from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("GitHub returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("GitHub returned an unexpected response")
    if payload.get("errors"):
        errors = payload["errors"]
        if not isinstance(errors, list):
            raise RuntimeError("GitHub returned an unexpected GraphQL error response")
        messages = "; ".join(
            str(item.get("message", "Unknown GraphQL error")).replace(token, "[redacted]")
            for item in errors if isinstance(item, dict)
        )
        raise RuntimeError(f"GitHub GraphQL error: {messages or 'Unknown GraphQL error'}")
    try:
        data = payload["data"]
    except KeyError as exc:
        raise RuntimeError("GitHub returned an unexpected response") from exc
    if not isinstance(data, dict):
        raise RuntimeError("GitHub returned an unexpected response")
    return data


def _count(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"GitHub returned missing or invalid {name}")
    return value


def _optional_count(value, name):
    return None if value is None else _count(value, name)


def _next_cursor(connection, current, name):
    page = connection.get("pageInfo") if isinstance(connection, dict) else None
    if not isinstance(page, dict) or not isinstance(page.get("hasNextPage"), bool):
        raise RuntimeError(f"GitHub returned invalid {name} pagination data")
    if not page["hasNextPage"]:
        return None
    cursor = page.get("endCursor")
    if not isinstance(cursor, str) or not cursor or cursor == current:
        raise RuntimeError(f"GitHub returned a non-advancing {name} pagination cursor")
    return cursor


def _include_repo(repo, include_private):
    if (not isinstance(repo, dict) or not isinstance(repo.get("id"), str)
            or not isinstance(repo.get("isPrivate"), bool) or not isinstance(repo.get("isFork"), bool)):
        raise RuntimeError("GitHub returned invalid contribution repository data")
    return include_private or not repo["isPrivate"]


def _get_stats(username, token, include_private):
    cursor = None
    stars = 0
    rank_stars = 0
    first_page = True
    stats = None
    while True:
        data = _post(_INFO_QUERY, {
            "login": username,
            "privacy": None if include_private else "PUBLIC",
            "after": cursor,
        }, token)
        user = data.get("user")
        if user is None:
            raise ValueError(f"GitHub user {username!r} was not found")
        viewer = data.get("viewer")
        if not isinstance(viewer, dict) or not isinstance(viewer.get("login"), str):
            raise RuntimeError("GitHub response did not contain viewer identity")
        if include_private and viewer["login"].casefold() != username.casefold():
            raise ValueError("private activity requires the requested user to authenticate")
        repo_page = user.get("repositories")
        if not isinstance(repo_page, dict) or not isinstance(repo_page.get("nodes"), list):
            raise RuntimeError("GitHub returned an invalid owned repository list")
        if first_page:
            try:
                created = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00")).date()
                rank_data = user["rankData"]
                private_access = _optional_count(viewer["privateRepos"]["totalCount"], "private access count")
                private_owned = _optional_count(user["privateOwned"]["totalCount"], "private repository count")
                stats = {
                    "created": created,
                    "rank_commits": _optional_count(rank_data["totalCommitContributions"], "commit contribution count"),
                    "rank_reviews": _optional_count(rank_data["totalPullRequestReviewContributions"], "review count"),
                    "rank_prs": _optional_count(user["pullRequests"]["totalCount"], "pull request count"),
                    "rank_issues": _count(user["openIssues"]["totalCount"], "issue count") + _count(user["closedIssues"]["totalCount"], "issue count"),
                    "followers": _optional_count(user["followers"]["totalCount"], "follower count"),
                    "repos": _optional_count(repo_page["totalCount"], "owned repository count"),
                    "private_access": private_access,
                    "private_owned": private_owned,
                    "restricted": rank_data["hasAnyRestrictedContributions"],
                }
            except (KeyError, TypeError, ValueError) as exc:
                raise RuntimeError("GitHub response did not contain activity data") from exc
            if not isinstance(stats["restricted"], bool):
                raise RuntimeError("GitHub returned missing restricted contribution status")
            if include_private and stats["restricted"]:
                raise RuntimeError("GitHub hid private contributions; enable private contribution visibility and grant read:user access")
            years = rank_data["contributionYears"]
            if not isinstance(years, list) or any(isinstance(year, bool) or not isinstance(year, int) for year in years):
                raise RuntimeError("GitHub returned invalid contribution years")
            stats["years"] = sorted(set(years))
            first_page = False
        for repo in repo_page["nodes"]:
            if not isinstance(repo, dict) or not isinstance(repo.get("isFork"), bool):
                raise RuntimeError("GitHub returned invalid owned repository data")
            repo_stars = _count(repo.get("stargazerCount"), "star count")
            rank_stars += repo_stars
            if not repo["isFork"]:
                stars += repo_stars
        cursor = _next_cursor(repo_page, cursor, "owned repositories")
        if cursor is None:
            stats["stars"] = stars
            stats["rank_stars"] = rank_stars
            return stats


def _repository_range(username, start, end, include_private, token, repositories):
    cursor = None
    first_page = True
    while True:
        data = _post(_REPOS_QUERY, {
            "login": username,
            "from": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "to": end.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "createdAfter": cursor,
        }, token)
        user = data.get("user")
        if not isinstance(user, dict) or not isinstance(user.get("contributionsCollection"), dict):
            raise RuntimeError("GitHub response did not contain dated repository contributions")
        collection = user["contributionsCollection"]
        if include_private and collection.get("hasAnyRestrictedContributions") is True:
            raise RuntimeError("GitHub hid private contributions; enable private contribution visibility and grant read:user access")
        lists = [
            collection.get("commitContributionsByRepository"),
            collection.get("issueContributionsByRepository"),
            collection.get("pullRequestContributionsByRepository"),
        ]
        if any(not isinstance(items, list) for items in lists):
            raise RuntimeError("GitHub returned invalid dated repository contributions")
        if first_page and any(len(items) >= REPOSITORY_LIMIT for items in lists):
            days = (end.date() - start.date()).days + 1
            if days <= 1:
                raise RuntimeError("GitHub contribution repository list reached its limit for a single day; exact totals are unavailable")
            midpoint = start.date() + timedelta(days=days // 2)
            left_end = datetime.combine(midpoint - timedelta(days=1), time.max, timezone.utc)
            right_start = datetime.combine(midpoint, time.min, timezone.utc)
            _repository_range(username, start, left_end, include_private, token, repositories)
            _repository_range(username, right_start, end, include_private, token, repositories)
            return
        if first_page:
            for items in lists:
                for item in items:
                    repo = item.get("repository") if isinstance(item, dict) else None
                    if _include_repo(repo, include_private):
                        repositories.add(repo["id"])
            first_page = False
        created = collection.get("repositoryContributions")
        if not isinstance(created, dict) or not isinstance(created.get("nodes"), list):
            raise RuntimeError("GitHub returned invalid repository creation contributions")
        for node in created["nodes"]:
            repo = node.get("repository") if isinstance(node, dict) else None
            if _include_repo(repo, include_private):
                repositories.add(repo["id"])
        cursor = _next_cursor(created, cursor, "repository creation contributions")
        if cursor is None:
            return


def _all_time_repositories(username, years, account_created, end_date, include_private, token):
    repositories = set()
    for year in years:
        start_day = max(account_created, date(year, 1, 1))
        end_day = min(end_date, date(year, 12, 31))
        if start_day > end_day:
            continue
        start = datetime.combine(start_day, time.min, timezone.utc)
        end = datetime.combine(end_day, time.max, timezone.utc).replace(microsecond=0)
        _repository_range(username, start, end, include_private, token, repositories)
    return len(repositories)


def _search_count(endpoint, query, name, token):
    headers = {"Accept": "application/vnd.github.cloak-preview" if endpoint == "commits" else "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(
            f"{API_URL}/search/{endpoint}", params={"q": query, "per_page": 1}, headers=headers, timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (403, 429):
            raise RuntimeError(f"GitHub API returned HTTP {status}; check token permissions or rate limits") from exc
        raise RuntimeError(f"GitHub API request failed{f' (HTTP {status})' if status else ''}") from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("GitHub returned invalid JSON") from exc
    if not isinstance(payload, dict) or payload.get("incomplete_results") is not False:
        raise RuntimeError(f"GitHub returned incomplete {name} search results")
    return _count(payload.get("total_count"), name)


def fetch_activity(username, token=None, *, end_date=None, all_commits=False, include_private=False):
    """Return lifetime activity through ``end_date`` plus current upstream rank inputs."""
    if not isinstance(username, str) or not username.strip():
        raise ValueError("GitHub username must not be empty")
    if not isinstance(include_private, bool) or not isinstance(all_commits, bool):
        raise ValueError("activity options must be booleans")
    token = _token(token)
    if not token:
        raise ValueError("Set GH_TOKEN or GITHUB_TOKEN to authenticate with GitHub")
    username = username.strip()
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", username):
        raise ValueError("Invalid GitHub username")
    if end_date is None:
        end_date = datetime.now(timezone.utc).date()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()
    if not isinstance(end_date, date):
        raise ValueError("end_date must be a date")

    stats = _get_stats(username, token, include_private)
    if end_date < stats["created"]:
        raise ValueError("end_date cannot be before the GitHub account creation date")
    start = stats["created"].isoformat()
    end = end_date.isoformat()
    date_filter = f"{start}..{end}"
    search_token = token if include_private else None
    commits = _search_count("commits", f"author:{username} author-date:{date_filter}", "commit count", search_token)
    pull_requests = _search_count("issues", f"author:{username} created:{date_filter} is:pr", "pull request count", search_token)
    issues = _search_count("issues", f"author:{username} created:{date_filter} is:issue", "issue count", search_token)
    repositories = _all_time_repositories(username, stats["years"], stats["created"], end_date, include_private, token)
    stars_as_of = datetime.now(timezone.utc).date()
    rank_allowed = end_date == stars_as_of and (
        include_private or (stats["private_access"] == 0 and stats["private_owned"] == 0 and not stats["restricted"])
    )
    rank_commits = _search_count("commits", f"author:{username}", "all-time commit count", search_token) if rank_allowed and all_commits else stats["rank_commits"]
    rank_inputs = None
    if rank_allowed:
        rank_inputs = {
            "commits": rank_commits, "prs": stats["rank_prs"],
            "issues": stats["rank_issues"], "reviews": stats["rank_reviews"],
            "repos": stats["repos"], "stars": stats["rank_stars"], "followers": stats["followers"],
        }
        if any(value is None for value in rank_inputs.values()):
            rank_inputs = None
    return {
        "start": start, "end": end, "stars_as_of": stars_as_of.isoformat(),
        "commits": commits, "pull_requests": pull_requests, "issues": issues,
        "repositories": repositories, "stars": stats["stars"], "rank_inputs": rank_inputs,
    }

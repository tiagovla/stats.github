"""Fetch and summarize language byte counts from owned GitHub repositories."""

from __future__ import annotations

import os
from urllib.parse import quote, urlsplit

import requests


API_URL = "https://api.github.com"


def _token(token):
    return token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")


def _get(url, token):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (403, 429):
            raise RuntimeError(f"GitHub API returned HTTP {status}; check token permissions or rate limits") from exc
        detail = f" (HTTP {status})" if status else ""
        raise RuntimeError(f"GitHub API request failed{detail}") from exc
    return response


def _json(response):
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("GitHub returned invalid JSON") from exc


def _pages(url, token):
    while url:
        target = urlsplit(url)
        origin = urlsplit(API_URL)
        if target.scheme != "https" or target.hostname != origin.hostname or target.port not in (None, 443):
            raise RuntimeError("GitHub returned an unsafe pagination URL")
        response = _get(url, token)
        payload = _json(response)
        if not isinstance(payload, list) or any(not isinstance(repo, dict) for repo in payload):
            raise RuntimeError("GitHub returned an unexpected repository list")
        yield from payload
        url = response.links.get("next", {}).get("url")


def fetch_language_data(
    username,
    token=None,
    *,
    include_private=False,
    include_forks=False,
    include_archived=True,
    include=(),
    exclude=(),
):
    """Return language byte totals for a user's owned repositories.

    Private repositories are included only by explicit opt-in and only when
    the token belongs to the requested user.
    """
    if not isinstance(username, str) or not username.strip():
        raise ValueError("GitHub username must not be empty")
    username = username.strip()
    token = _token(token)
    if include_private and not token:
        raise ValueError("Set GH_TOKEN or GITHUB_TOKEN to include private repositories")

    if include_private:
        account = _json(_get(f"{API_URL}/user", token))
        if not isinstance(account, dict) or account.get("login", "").casefold() != username.casefold():
            raise ValueError("Private repositories can only be fetched for the authenticated GitHub user")
        repos_url = f"{API_URL}/user/repos?visibility=all&affiliation=owner&per_page=100"
    else:
        repos_url = f"{API_URL}/users/{quote(username, safe='')}/repos?type=owner&per_page=100"

    allowed, excluded = set(include), set(exclude)
    totals = {}
    for repo in _pages(repos_url, token):
        name = repo.get("name")
        if not isinstance(name, str):
            raise RuntimeError("GitHub returned a repository without a name")
        owner_data = repo.get("owner")
        owner = owner_data.get("login") if isinstance(owner_data, dict) else None
        if not isinstance(owner, str) or owner.casefold() != username.casefold():
            continue
        if repo.get("private") and not include_private:
            continue
        if (repo.get("fork") and not include_forks) or (repo.get("archived") and not include_archived):
            continue
        if (allowed and name not in allowed) or name in excluded:
            continue
        url = f"{API_URL}/repos/{quote(owner, safe='')}/{quote(name, safe='')}/languages"
        languages = _json(_get(url, token))
        if not isinstance(languages, dict) or any(
            not isinstance(language, str) or isinstance(size, bool) or not isinstance(size, int) or size < 0
            for language, size in languages.items()
        ):
            raise RuntimeError("GitHub returned invalid repository language data")
        for language, size in languages.items():
            totals[language] = totals.get(language, 0) + size
    return totals


def aggregate_languages(language_bytes, top=7):
    """Return the largest language totals without changing their byte counts."""
    if isinstance(top, bool) or not isinstance(top, int) or top < 0:
        raise ValueError("top must be a nonnegative integer")
    if not isinstance(language_bytes, dict) or any(
        not isinstance(name, str) or isinstance(size, bool) or not isinstance(size, int) or size < 0
        for name, size in language_bytes.items()
    ):
        raise ValueError("language bytes must map names to nonnegative integers")
    ranked = sorted(language_bytes.items(), key=lambda item: (-item[1], item[0]))
    return dict(ranked[:top])

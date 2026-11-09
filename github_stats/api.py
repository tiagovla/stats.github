"""GitHub GraphQL client for contribution calendar data."""

import os

import requests


GRAPHQL_URL = "https://api.github.com/graphql"
_CALENDAR_QUERY = """
query ContributionCalendar($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""


def fetch_calendar(username, token=None):
    """Fetch GitHub's contributionCalendar object for a username."""
    if not isinstance(username, str) or not username.strip():
        raise ValueError("GitHub username must not be empty")

    token = token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("Set GH_TOKEN or GITHUB_TOKEN to authenticate with GitHub")

    try:
        response = requests.post(
            GRAPHQL_URL,
            json={"query": _CALENDAR_QUERY, "variables": {"login": username.strip()}},
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (403, 429):
            raise RuntimeError(f"GitHub API returned HTTP {status}; check token permissions or rate limits") from exc
        # Exception text can include request headers, so never forward it.
        detail = f" (HTTP {status})" if status else ""
        raise RuntimeError(f"GitHub API request failed{detail}") from exc

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
        user = payload["data"]["user"]
        if user is None:
            raise ValueError(f"GitHub user {username.strip()!r} was not found")
        calendar = user["contributionsCollection"]["contributionCalendar"]
        if not isinstance(calendar["weeks"], list):
            raise TypeError("calendar weeks must be a list")
    except (KeyError, TypeError) as exc:
        raise RuntimeError("GitHub response did not contain a contribution calendar") from exc
    return calendar

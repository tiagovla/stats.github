"""Port of ``calculateRank`` from github-stats-extended.

Source: stats-organization/github-stats-extended, commit
fe0684b3d454ee6b558b60d7f3d90f1027a8c0f8, packages/core/src/calculateRank.ts.
See UPSTREAM_LICENSE for the MIT license notice.
"""

from __future__ import annotations


def _exponential_cdf(value: float) -> float:
    return 1 - 2**-value


def _log_normal_cdf(value: float) -> float:
    return value / (1 + value)


def calculate_rank(
    *,
    all_commits: bool,
    commits: float,
    prs: float,
    issues: float,
    reviews: float,
    repos: float,
    stars: float,
    followers: float,
) -> dict[str, str | float]:
    """Calculate the upstream rank level and percentile; ``repos`` is unused."""
    commits_median = 1000 if all_commits else 250
    total_weight = 2 + 3 + 1 + 1 + 4 + 1

    rank = 1 - (
        2 * _exponential_cdf(commits / commits_median)
        + 3 * _exponential_cdf(prs / 50)
        + _exponential_cdf(issues / 25)
        + _exponential_cdf(reviews / 2)
        + 4 * _log_normal_cdf(stars / 50)
        + _log_normal_cdf(followers / 10)
    ) / total_weight

    thresholds = (1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100)
    levels = ("S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C")
    level = next((level for threshold, level in zip(thresholds, levels) if rank * 100 <= threshold), None)
    if level is None:
        raise RuntimeError("Unable to determine rank level")
    return {"level": level, "percentile": rank * 100}

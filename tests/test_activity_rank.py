from math import log2

import pytest

from github_stats.activity_rank import calculate_rank


def stats(**overrides):
    result = {
        "all_commits": False,
        "commits": 0,
        "prs": 0,
        "issues": 0,
        "reviews": 0,
        "repos": 0,
        "stars": 0,
        "followers": 0,
    }
    result.update(overrides)
    return result


def test_empty_activity_is_lowest_rank_and_repos_does_not_affect_score():
    result = calculate_rank(**stats())

    assert result == {"level": "C", "percentile": 100.0}
    assert calculate_rank(**stats(repos=1000)) == result


def test_all_commits_changes_only_commit_median():
    limited = calculate_rank(**stats(commits=250))
    all_commits = calculate_rank(**stats(commits=250, all_commits=True))

    assert limited["percentile"] == pytest.approx(100 * (1 - (2 / 12) * (1 - 2**-1)))
    assert all_commits["percentile"] == pytest.approx(100 * (1 - (2 / 12) * (1 - 2**-0.25)))


def test_weighted_exponential_and_log_normal_scores_match_upstream():
    result = calculate_rank(**stats(commits=250, prs=50, issues=25, reviews=2, stars=50, followers=10))
    expected_rank = 1 - (2 * 0.5 + 3 * 0.5 + 0.5 + 0.5 + 4 * 0.5 + 0.5) / 12

    assert result["level"] == "B+"
    assert result["percentile"] == pytest.approx(expected_rank * 100)


def test_percentile_thresholds_select_the_first_matching_level():
    # Commits alone contribute 2/12 of the exponential CDF; choose a value
    # whose resulting rank lands exactly on the 87.5% threshold.
    commits = -250 * log2(1 - 0.125 * 12 / 2)

    assert calculate_rank(**stats(commits=commits)) == {"level": "C+", "percentile": pytest.approx(87.5)}


def test_unrankable_values_raise_upstream_error():
    with pytest.raises(RuntimeError, match="Unable to determine rank level"):
        calculate_rank(**stats(commits=-1000))

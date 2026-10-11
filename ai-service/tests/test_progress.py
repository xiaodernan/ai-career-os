"""Unit tests for skill-progress tracking (forward Epic 10.6).

A set diff over two gap reports' own verdicts. The tests pin the four moves
(closed / improved / regressed / opened), the baseline case, and the counts.
"""

from app.features.progress import diff_progress, skill_states

PREV = {"targetRole": "Senior Backend Engineer", "coverage": 0.4,
        "covered": [{"skill": "Java"}],
        "partial": [{"skill": "Redis"}],
        "gaps": [{"skill": "Kubernetes"}, {"skill": "Go"}]}
CUR = {"targetRole": "Senior Backend Engineer", "coverage": 0.7,
       "covered": [{"skill": "Java"}, {"skill": "Kubernetes"}],
       "partial": [{"skill": "Go"}],
       "gaps": [{"skill": "Rust"}]}


# ---------------- skill_states ----------------


def test_skill_states_maps_the_three_lists():
    states = skill_states({"covered": [{"skill": "A"}], "partial": [{"skill": "B"}],
                           "gaps": [{"skill": "C"}]})
    assert states == {"A": "covered", "B": "partial", "C": "gap"}


def test_skill_states_covered_wins_a_conflict():
    states = skill_states({"covered": [{"skill": "A"}], "gaps": [{"skill": "A"}]})
    assert states == {"A": "covered"}


def test_skill_states_ignores_blank_names():
    assert skill_states({"covered": [{"skill": ""}], "gaps": [{"skill": "B"}]}) == {"B": "gap"}


# ---------------- diff_progress ----------------


def test_diff_reports_all_four_moves():
    d = diff_progress(PREV, CUR)
    assert d["baseline"] is False
    assert d["closed"] == ["Kubernetes"]     # gap -> covered
    assert d["improved"] == ["Go"]           # gap -> partial
    assert d["opened"] == ["Rust"]           # new gap, not in the previous report
    assert d["regressed"] == []              # nothing fell back


def test_diff_counts_and_coverage_delta():
    d = diff_progress(PREV, CUR)
    assert d["previousCoverage"] == 0.4 and d["currentCoverage"] == 0.7
    assert d["delta"] == 0.3
    assert d["closedCount"] == 1
    assert d["openCount"] == 1               # only Rust is open now (opened ⊆ stillOpen)


def test_diff_still_open_excludes_closed_and_improved():
    d = diff_progress(PREV, CUR)
    # Go improved (partial) and Kubernetes closed are not "still open"
    assert d["stillOpen"] == ["Rust"]


def test_diff_baseline_when_no_previous():
    d = diff_progress(None, CUR)
    assert d["baseline"] is True
    assert d["closed"] == [] and d["improved"] == [] and d["opened"] == []
    assert d["stillOpen"] == ["Go", "Rust"]
    assert d["delta"] == 0.7


def test_diff_detects_regression():
    d = diff_progress({"covered": [{"skill": "Java"}]}, {"gaps": [{"skill": "Java"}]})
    assert d["regressed"] == ["Java"]
    assert d["closed"] == []


def test_diff_empty_reports():
    d = diff_progress(None, {})
    assert d["closed"] == [] and d["stillOpen"] == [] and d["delta"] == 0.0

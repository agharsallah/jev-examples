"""The overview's composites and links are plain code over answers; so are these tests."""

from datetime import UTC, datetime

import pytest

from triage.overview import BEGINNER, READINESS, breakdown, edges, row, scores


def _score(value, levels):
    return {
        "type": "score",
        "score": value,
        "levels": levels,
        "confidence": 1.0,
        "probabilities": {},
    }


def _answers(kind="bug", **nouls):
    answers = {
        "kind": {"type": "choice", "choice": kind, "probabilities": {kind: 1.0}, "confidence": 1.0},
        "actionability": _score(3, 4),
        "clarity": _score(3, 4),
        "scope": _score(0, 4),
        "newcomer": _score(3, 4),
    }
    for key, value in nouls.items():
        answers[key] = {"type": "noul", "noul": value}
    return answers


def test_weights_are_a_definition_that_sums_to_one():
    assert sum(READINESS.values()) == pytest.approx(1.0)
    assert sum(BEGINNER.values()) == pytest.approx(1.0)


def test_a_clear_decided_reproducible_bug_is_fully_ready():
    s = scores(_answers(needs_decision=0.0, multiple_problems=0.0, has_repro_steps=1.0))
    assert s["readiness"] == pytest.approx(1.0)
    assert s["beginner"] == pytest.approx(1.0)


def test_an_open_decision_costs_exactly_its_weight():
    decided = scores(_answers(needs_decision=0.0, has_repro_steps=1.0))["readiness"]
    open_q = scores(_answers(needs_decision=1.0, has_repro_steps=1.0))["readiness"]
    assert decided - open_q == pytest.approx(READINESS["decided"])


def test_repro_only_counts_for_bugs():
    feature = scores(_answers(kind="feature", has_repro_steps=0.0))
    assert feature["readiness_parts"]["reproducible"] == 1.0
    bug = scores(_answers(kind="bug", has_repro_steps=0.0))
    assert bug["readiness_parts"]["reproducible"] == 0.0


def test_the_recorded_issue_as_an_overview_row(measurement):
    r = row(measurement, datetime(2026, 9, 30, 12, tzinfo=UTC))
    assert r["number"] == 8107 and r["kind"] == "bug"
    assert r["age_days"] == 7
    assert 0 <= r["readiness"] <= 1 and 0 <= r["beginner"] <= 1
    assert r["beginner_label"] == "good first issue"
    # The labels already on the issue are never suggested again.
    assert all(s["label"] not in measurement["issue"]["labels"] for s in r["suggested"])


def test_only_pairs_that_might_clear_a_threshold_are_kept(measurement):
    found = edges(measurement)
    numbers = {e["b"] for e in found}
    assert {7212, 8101} <= numbers  # related, not the same problem
    assert all(e["same"] >= 0.40 or e["related"] >= 0.60 for e in found)


def test_breakdown_counts_components_by_kind():
    rows = [
        {"component": "api", "kind": "bug", "lane": "auto"},
        {"component": "api", "kind": "feature", "lane": "confirm"},
        {"component": None, "kind": "bug", "lane": "auto"},
    ]
    b = breakdown(rows)
    assert b["component_kind"][0] == {
        "component": "api",
        "total": 2,
        "kinds": {"bug": 1, "feature": 1},
    }
    assert b["lanes"] == {"auto": 2, "confirm": 1}

"""The evaluation's arithmetic, on hand-built answers where the right numbers are obvious."""

import pytest

from triage.evaluate import family_report
from triage.taxonomy import Family

FAMILY = Family(
    key="type", role="issue_type", title="type", labels=["Bug", "Feature"], mode="choice"
)


def _m(number, on_it, pick, p, confidence=None):
    other = "Feature" if pick == "Bug" else "Bug"
    return {
        "issue": {"number": number, "title": f"#{number}", "url": "", "labels": on_it},
        "answers": {
            "fam__type": {
                "type": "choice",
                "choice": pick,
                "probabilities": {pick: p, other: 1 - p, "none_fit": 0.0},
                "confidence": confidence if confidence is not None else p,
            }
        },
    }


def test_agreement_counts_only_issues_that_carry_a_family_label():
    report = family_report(
        FAMILY,
        [
            _m(1, ["Bug"], "Bug", 0.9),
            _m(2, ["Feature"], "Bug", 0.8),
            _m(3, ["triaged"], "Bug", 0.9),
        ],
    )
    assert report["n"] == 2
    assert report["agreement"] == 0.5
    assert report["top2"] == 1.0


def test_a_perfectly_calibrated_bin_has_no_error():
    # Ten issues at p=0.8, eight of them right: said 0.8, was right 0.8 of the time.
    ms = [_m(i, ["Bug"] if i < 8 else ["Feature"], "Bug", 0.8) for i in range(10)]
    report = family_report(FAMILY, ms)
    assert report["ece"] == pytest.approx(0.0, abs=1e-9)
    assert report["reliability"] == [
        {"bin": 8, "lo": 0.8, "hi": 0.9, "n": 10, "mean_p": pytest.approx(0.8), "accuracy": 0.8}
    ]


def test_raising_the_bar_trades_coverage_for_agreement():
    ms = [_m(1, ["Bug"], "Bug", 0.95), _m(2, ["Bug"], "Bug", 0.9), _m(3, ["Feature"], "Bug", 0.55)]
    coverage = {c["threshold"]: c for c in family_report(FAMILY, ms)["coverage"]}
    assert coverage[0.0]["coverage"] == 1.0
    assert coverage[0.0]["accuracy"] == pytest.approx(2 / 3)
    assert coverage[0.6]["coverage"] == pytest.approx(2 / 3)
    assert coverage[0.6]["accuracy"] == 1.0


def test_the_most_common_confusion_is_named():
    ms = [_m(i, ["Feature"], "Bug", 0.9) for i in range(3)] + [_m(9, ["Bug"], "Bug", 0.9)]
    report = family_report(FAMILY, ms)
    assert report["confusions"][0] == {"truth": "Feature", "pick": "Bug", "n": 3}
    assert report["top_confusion_share"] == 1.0
    assert [d["number"] for d in report["disagreements"]] == [0, 1, 2]


def test_no_labelled_issues_means_no_report():
    assert family_report(FAMILY, [_m(1, ["triaged"], "Bug", 0.9)]) is None

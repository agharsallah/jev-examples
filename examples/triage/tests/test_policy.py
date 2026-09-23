"""The verdict is plain code: these tests move the numbers and watch it follow."""

from triage.triage import verdict


def test_the_recorded_issue_is_ready(measurement):
    a = verdict(measurement)
    assert a.lane == "auto"
    assert {"Bug", "P2-medium"} <= {label["label"] for label in a.labels}
    assert a.missing == []
    assert a.reply is None


def test_related_is_not_duplicate(measurement):
    """#7212 and #8101 were flagged as 'may be related'; the reporter said
    neither is the same problem. Jev's two questions keep that distinction."""
    a = verdict(measurement)
    by_number = {d["number"]: d for d in a.duplicates}
    assert by_number[7212]["verdict"] == "related"
    assert by_number[8101]["verdict"] == "related"
    assert "duplicate" not in a.lanes


def test_a_bug_missing_essentials_asks_the_reporter(measurement):
    for key in ("has_repro_steps", "has_environment"):
        measurement["answers"][key]["noul"] = 0.1
    a = verdict(measurement)
    assert a.lane == "needs_info"
    assert "exact steps" in a.reply and "version" in a.reply


def test_security_outranks_everything(measurement):
    measurement["answers"]["security_sensitive"]["noul"] = 0.9
    assert verdict(measurement).lane == "private"


def test_steering_text_goes_to_a_human(measurement):
    measurement["answers"]["steers_triage"]["noul"] = 0.95
    assert verdict(measurement).lane == "human"


def test_thresholds_are_settings_not_constants(measurement):
    strict = verdict(measurement, {"choice_apply": 0.99})
    assert strict.lane == "confirm"
    loose = verdict(measurement, {"dup_same": 0.1})
    assert loose.lanes[0] == "duplicate"


def test_weights_move_priority_without_new_answers(measurement):
    impact_only = verdict(
        measurement, {"weights": {"impact": 1.0, "actionability": 0.0, "frustration": 0.0}}
    )
    impact = measurement["answers"]["impact"]
    assert abs(impact_only.priority - impact["score"] / (impact["levels"] - 1)) < 1e-3


def test_label_drift_needs_a_confident_disagreement(measurement):
    a = verdict(measurement)
    assert [d["current"] for d in a.drift] == ["comp:harness-t2"]
    assert verdict(measurement, {"drift_winner": 0.99}).drift == []


def test_evidence_ranks_units_for_the_decided_kind(measurement):
    a = verdict(measurement)
    rows = a.evidence["kind"]
    assert rows[0]["target"] == "bug"
    assert rows == sorted(rows, key=lambda r: -r["p_target"])

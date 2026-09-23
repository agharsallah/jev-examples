import pytest

from triage.github import Label
from triage.taxonomy import build_families, prefix_of, usage_bucket


@pytest.mark.parametrize(
    ("name", "prefix"),
    [
        ("comp:server", "comp"),
        ("area/cli", "area"),
        ("focus: ux", "focus"),
        ("P1-high", "p"),
        ("severity:S2", "severity"),
        ("S2", "s"),
        ("Bug", None),
        ("good first issue", None),
    ],
)
def test_prefix_of(name, prefix):
    assert prefix_of(name) == prefix


def test_counts_go_to_jev_as_words():
    assert [usage_bucket(n) for n in (0, 3, 20, 900)] == ["never", "rarely", "sometimes", "often"]


def _roles(**named):
    return {
        name: {
            "role": role,
            "confidence": 1.0,
            "probabilities": {},
            "prefix": prefix_of(name),
            "issues": 10,
        }
        for name, role in named.items()
    }


def test_a_prefix_group_takes_its_majority_role():
    roles = _roles(**{"comp:a": "component", "comp:b": "component", "comp:c": "release"})
    families = build_families([Label(n) for n in roles], roles, {})
    assert [(f.key, sorted(f.labels)) for f in families] == [
        ("component", ["comp:a", "comp:b", "comp:c"])
    ]


def test_roles_decide_how_a_family_is_asked():
    roles = _roles(
        Bug="issue_type",
        Feature="issue_type",
        **{"good first issue": "attribute", "triaged": "workflow_status", "0.3.0": "release"},
    )
    ignored: dict[str, str] = {}
    families = build_families([Label(n) for n in roles], roles, ignored)
    assert {f.key: f.mode for f in families} == {"type": "choice", "attribute": "nouls"}
    assert set(ignored) == {"triaged", "0.3.0"}


def test_a_family_of_one_is_not_a_choice():
    roles = _roles(Bug="issue_type")
    ignored: dict[str, str] = {}
    assert build_families([Label("Bug")], roles, ignored) == []
    assert "Bug" in ignored


def test_the_omnigent_reading(tax):
    families = {f.key: f for f in tax.families}
    assert set(families["type"].labels) == {"Bug", "Feature", "Docs"}
    assert all(n.startswith("comp:") or n == "git-credential" for n in families["component"].labels)
    assert set(families["priority"].labels) == {"P0-critical", "P1-high", "P2-medium", "P3-low"}
    assert tax.ignored["size/L"] == "only on pull requests"
    assert tax.ignored["triaged"] == "process or automation state"

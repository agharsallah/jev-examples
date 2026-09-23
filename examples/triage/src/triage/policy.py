"""The verdict. Plain Python over numbers; it never touches the network.

Jev never says "label this P1" or "close it". It returns probabilities, and
this module decides — with every threshold named, every rule written down,
and a trace of which rule fired on which number. Change a threshold or a
weight and the whole assessment is recomputed from the same answers, which is
what the sliders in the browser do.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .questions import NONE_FIT
from .taxonomy import Family, Taxonomy

DEFAULTS: dict = {
    # A family label is applied without asking when its Choice is this sure…
    "choice_apply": 0.70,
    # …suggested for confirmation above this, and left to a human below it.
    "choice_floor": 0.40,
    # A per-label Noul: apply above, suggest above confirm.
    "noul_apply": 0.80,
    "noul_confirm": 0.55,
    # A checklist item counts as present above this.
    "present": 0.50,
    "security": 0.60,
    "steer": 0.60,
    "low_effort": 0.70,
    "resolved": 0.75,
    "dup_same": 0.75,
    "dup_related": 0.60,
    # Label drift: Jev's pick this sure, while the label already on it is this unlikely.
    "drift_winner": 0.80,
    "drift_existing": 0.10,
    # Priority is a weighted blend of normalised Scores (each 0..1).
    "weights": {"impact": 0.6, "actionability": 0.25, "frustration": 0.15},
}

# What each missing piece of a bug report costs the maintainer, as the line a
# reply would ask for. Selected by code, never written by a model.
REPLY_LINES = {
    "has_repro_steps": "the exact steps, command or a minimal snippet that triggers it",
    "has_expected_vs_actual": "what you expected to happen, and what happened instead",
    "has_environment": "the version you are on and your environment (OS, runtime, install method)",
    "has_error_output": "the full error message or log output",
}
BUG_ESSENTIALS = ("has_repro_steps", "has_expected_vs_actual", "has_environment")

LANES = {
    "private": "Handle privately — possible security issue",
    "human": "Needs a human",
    "close": "Close candidate",
    "duplicate": "Possible duplicate",
    "needs_info": "Ask the reporter",
    "auto": "Ready — labels can be applied",
    "confirm": "Ready — confirm the suggested labels",
}


@dataclass
class Rule:
    """One line of the policy trace."""

    rule: str
    value: float | str | None
    threshold: float | str | None
    fired: bool
    note: str = ""


@dataclass
class Assessment:
    lane: str
    lanes: list[str]
    labels: list[dict]
    priority: float
    priority_parts: dict[str, float]
    missing: list[str]
    reply: str | None
    duplicates: list[dict]
    drift: list[dict]
    evidence: dict[str, list[dict]]
    trace: list[Rule] = field(default_factory=list)


def _noul(answers: dict, key: str) -> float:
    return answers[key]["noul"] if key in answers else 0.0


def _norm(answer: dict) -> float:
    return answer["score"] / max(1, answer["levels"] - 1)


def assess(
    answers: dict,
    taxonomy: Taxonomy,
    *,
    candidates: list[dict] | None = None,
    units: list[dict] | None = None,
    existing: list[str] | None = None,
    settings: dict | None = None,
) -> Assessment:
    """Turn one issue's answers into a verdict, and say why."""
    s = {**DEFAULTS, **(settings or {})}
    s["weights"] = {**DEFAULTS["weights"], **(settings or {}).get("weights", {})}
    trace: list[Rule] = []
    candidates = candidates or []
    existing = existing or []

    def check(rule: str, value, threshold, fired: bool, note: str = "") -> bool:
        trace.append(Rule(rule, value, threshold, fired, note))
        return fired

    kind = answers["kind"]
    is_bug = kind["choice"] == "bug"

    # -- labels from the repo's own families ------------------------------
    labels: list[dict] = []
    uncertain_families: list[str] = []
    for family in taxonomy.families:
        labels += _family_labels(family, answers, s, check, uncertain_families)

    # -- the checklist ----------------------------------------------------
    missing = []
    if is_bug:
        for key in BUG_ESSENTIALS:
            present = _noul(answers, key)
            if not check(
                f"bug report has {key[4:].replace('_', ' ')}",
                present,
                s["present"],
                present >= s["present"],
            ):
                missing.append(key)
        if _noul(answers, "has_error_output") < s["present"] and "has_repro_steps" in missing:
            missing.append("has_error_output")

    # -- duplicates -------------------------------------------------------
    duplicates = []
    for i, candidate in enumerate(candidates):
        same, related = _noul(answers, f"dup__{i}__same"), _noul(answers, f"dup__{i}__related")
        verdict = (
            "duplicate"
            if same >= s["dup_same"]
            else "related"
            if related >= s["dup_related"]
            else "unrelated"
        )
        duplicates.append({**candidate, "same": same, "related": related, "verdict": verdict})
    duplicates.sort(key=lambda d: (-d["same"], -d["related"]))

    # -- label drift: what is on the issue vs what Jev reads --------------
    drift = []
    for family in taxonomy.families:
        answer = answers.get(f"fam__{family.key}")
        if family.mode != "choice" or not answer:
            continue
        on_issue = [n for n in existing if n in family.labels]
        winner, p = answer["choice"], answer["probabilities"].get(answer["choice"], 0.0)
        for name in on_issue:
            theirs = answer["probabilities"].get(name, 0.0)
            if (
                winner not in (name, NONE_FIT)
                and p >= s["drift_winner"]
                and theirs <= s["drift_existing"]
            ):
                drift.append(
                    {
                        "family": family.title,
                        "current": name,
                        "suggested": winner,
                        "p_current": theirs,
                        "p_suggested": p,
                    }
                )

    # -- priority ---------------------------------------------------------
    parts = {name: _norm(answers[name]) for name in s["weights"] if name in answers}
    total = sum(s["weights"][n] for n in parts) or 1.0
    priority = sum(s["weights"][n] * v for n, v in parts.items()) / total

    # -- lanes, most urgent first -----------------------------------------
    lanes: list[str] = []
    security = _noul(answers, "security_sensitive")
    if check("security-sensitive", security, s["security"], security >= s["security"]):
        lanes.append("private")
    steer = _noul(answers, "steers_triage")
    if check(
        "text tries to steer triage",
        steer,
        s["steer"],
        steer >= s["steer"],
        "a human reads it; the labels below are not applied",
    ):
        lanes.append("human")
    low = _noul(answers, "low_effort")
    if check("spam or low effort", low, s["low_effort"], low >= s["low_effort"]):
        lanes.append("close")
    resolved = max(_noul(answers, "fixed_in_thread"), _noul(answers, "reporter_confirmed"))
    if check("resolved in the thread", resolved, s["resolved"], resolved >= s["resolved"]):
        lanes.append("close")
    if duplicates and check(
        "same problem as a candidate",
        duplicates[0]["same"],
        s["dup_same"],
        duplicates[0]["same"] >= s["dup_same"],
        f"#{duplicates[0]['number']}",
    ):
        lanes.append("duplicate")
    if is_bug and check(
        "bug report missing essentials",
        len(missing),
        "≥ 2",
        len(missing) >= 2,
        ", ".join(m[4:].replace("_", " ") for m in missing),
    ):
        lanes.append("needs_info")
    kind_sure = kind["confidence"]
    if check(
        "unsure what kind of report it is",
        kind_sure,
        f"< {s['choice_floor']}",
        kind_sure < s["choice_floor"],
        "confidence of the kind Choice",
    ):
        lanes.append("human")
    if uncertain_families:
        # Not a reason to hand the issue over: that family's label is simply
        # not suggested, and the rest of the verdict stands.
        check(
            "families left unlabelled (below the floor)",
            ", ".join(uncertain_families),
            s["choice_floor"],
            True,
            "no label suggested",
        )
    if not lanes:
        auto = all(
            label["status"] == "apply"
            for label in labels
            if label["family_mode"] == "choice" and label["status"] != "unsure"
        )
        lanes.append("auto" if auto else "confirm")
    lanes = list(dict.fromkeys(lanes))

    reply = None
    if "needs_info" in lanes and missing:
        asks = "\n".join(f"- {REPLY_LINES[m]}" for m in missing)
        reply = (
            "Thanks for the report! To look into this we need a little more:\n"
            f"{asks}\n\nOnce that's here we can pick it up."
        )

    return Assessment(
        lane=lanes[0],
        lanes=lanes,
        labels=labels,
        priority=round(priority, 4),
        priority_parts=parts,
        missing=missing,
        reply=reply,
        duplicates=duplicates,
        drift=drift,
        evidence=evidence(answers, units or [], taxonomy),
        trace=trace,
    )


def _family_labels(
    family: Family, answers: dict, s: dict, check, uncertain: list[str]
) -> list[dict]:
    found = []
    if family.mode == "choice":
        answer = answers.get(f"fam__{family.key}")
        if not answer:
            return found
        choice, confidence = answer["choice"], answer["confidence"]
        if choice == NONE_FIT:
            check(
                f"{family.title}: none of the labels fits",
                answer["probabilities"][NONE_FIT],
                None,
                True,
            )
            return found
        if confidence >= s["choice_apply"]:
            status = "apply"
        elif confidence >= s["choice_floor"]:
            status = "confirm"
        else:
            status = "unsure"
            uncertain.append(family.title)
        check(
            f"{family.title} → {choice}",
            confidence,
            s["choice_apply"],
            status == "apply",
            "confidence" + ("" if status == "apply" else f"; {status}"),
        )
        found.append(
            {
                "label": choice,
                "family": family.title,
                "family_mode": "choice",
                "p": answer["probabilities"][choice],
                "confidence": confidence,
                "status": status,
            }
        )
        return found

    for i, name in enumerate(family.labels):
        p = _noul(answers, f"lab__{family.key}__{i}")
        if p >= s["noul_apply"]:
            status = "apply"
        elif p >= s["noul_confirm"]:
            status = "confirm"
        else:
            continue
        check(f"{name}", p, s["noul_apply"], status == "apply", status)
        found.append(
            {
                "label": name,
                "family": family.title,
                "family_mode": "nouls",
                "p": p,
                "confidence": None,
                "status": status,
            }
        )
    return found


def evidence(answers: dict, units: list[dict], taxonomy: Taxonomy) -> dict[str, list[dict]]:
    """Which units of the text point at the decided kind and component.

    Each unit's Choice says what that part of the text signals on its own.
    Code picks out the units that agree with the overall decision and ranks
    them — that list is what the highlights, and the counterfactuals, use.
    """
    out: dict[str, list[dict]] = {}
    targets = {"kind": answers["kind"]["choice"]}
    component = taxonomy.family("component")
    if component and f"fam__{component.key}" in answers:
        targets["comp"] = answers[f"fam__{component.key}"]["choice"]
    for dim, target in targets.items():
        rows = []
        for unit in units:
            answer = answers.get(f"u{unit['index']}__{dim}")
            if not answer:
                continue
            rows.append(
                {
                    "index": unit["index"],
                    "signal": answer["choice"],
                    "p_target": answer["probabilities"].get(target, 0.0),
                    "p_neutral": answer["probabilities"].get("neutral", 0.0),
                    "probabilities": answer["probabilities"],
                }
            )
        rows.sort(key=lambda r: -r["p_target"])
        out[dim] = [{"target": target, **r} for r in rows]
    return out

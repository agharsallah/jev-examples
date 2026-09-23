"""Applying the rules in `rules.py` to one set of answers."""

from __future__ import annotations

from .model import Finding
from .rules import ASK_INTENTS, ASK_RULES, CHECK_RULES, INTENT_RULES, INTENT_SCORE_RULES, Rule

SEVERITY_ORDER = {"blocker": 0, "major": 1, "minor": 2, "good": 3}


def findings_for(answers, intent: str) -> list[Finding]:
    """Every finding that fires for this draft, given what it is trying to do."""
    findings = _collect(answers, CHECK_RULES, "noul")
    if intent in ASK_INTENTS:
        findings += _collect(answers, ASK_RULES, "noul")
    findings += _collect(answers, INTENT_RULES.get(intent, []), "noul")
    findings += _collect(answers, INTENT_SCORE_RULES.get(intent, []), "score")
    return _dedupe(findings)


def _fires(value: float, direction: str, threshold: float) -> bool:
    return value > threshold if direction == "above" else value < threshold


def _collect(answers, rules: list[Rule], kind: str) -> list[Finding]:
    found: list[Finding] = []
    for key, direction, threshold, severity, title, fix in rules:
        answer = answers.get(key)
        if answer is None:
            continue
        value = float(answer.noul) if kind == "noul" else float(answer.score)
        if not _fires(value, direction, threshold):
            continue
        support = value if kind == "noul" else value / 4
        found.append(
            Finding(
                key=key,
                severity=severity,
                title=title,
                fix=fix,
                value=value,
                strength=support if direction == "above" else 1 - support,
            )
        )
    return found


def _dedupe(findings: list[Finding]) -> list[Finding]:
    """Keep the most severe finding per question; several rules can fire."""
    best: dict[str, Finding] = {}
    for finding in findings:
        current = best.get(finding.key)
        if current is None or SEVERITY_ORDER[finding.severity] < SEVERITY_ORDER[current.severity]:
            best[finding.key] = finding
    return sorted(best.values(), key=lambda f: (SEVERITY_ORDER[f.severity], -f.strength))

"""From positions on a scale to one number and one verdict.

Rails first (how far each dimension missed this reader's band), then fit (the
rails averaged), then the send score (fit with the findings charged against
it), then the verdict (the send score, unless something overrides it).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from ..audience import UNSURE, Audience, Band
from ..questions import DIMENSIONS
from .model import HOLD, REWRITE, SEND, TIGHTEN, UNCLEAR, Finding, Rail

# Below this, Jev cannot tell what the draft is for -- which is almost always a
# fact about the draft rather than about the model.
INTENT_FLOOR = 0.45

# What each finding costs the headline score. A draft can be pitched perfectly
# for its reader and still not be sendable, which is why fit alone is not it.
SEVERITY_COST = {"blocker": 0, "major": 12, "minor": 4, "good": -3}

# However well the rest reads, a blocker caps the number here.
BLOCKER_CEILING = 25


class Measured(Protocol):
    """What a rail keeps from Jev when the reader changes: a rail, or its JSON."""

    key: str
    score: float
    confidence: float
    level: str
    counted: bool


def _rail(key: str, score: float, confidence: float, counted: bool, level: str, band: Band) -> Rail:
    return Rail(
        key=key,
        label=key.replace("_", " "),
        score=score,
        confidence=confidence,
        low=band.low,
        high=band.high,
        weight=band.weight,
        miss=band.miss(score),
        counted=counted,
        level=level,
    )


def rails_for(answers, audience: Audience) -> list[Rail]:
    """Where the draft landed on each dimension, against this reader's bands."""
    rails: list[Rail] = []
    for key in DIMENSIONS:
        answer = answers.get(key)
        band = audience.bands.get(key)
        if answer is None or band is None:
            continue
        score = float(answer.score)
        confidence = float(answer.confidence)
        level = answer.legend.get(int(round(score)), "")
        rails.append(_rail(key, score, confidence, confidence >= UNSURE, level, band))
    return rails


def rails_against(measured: Iterable[Measured], audience: Audience) -> list[Rail]:
    """The same measurements, laid against a different reader's bands.

    Whether a rail counts is a fact about Jev's confidence, not about the
    reader, so it is carried over rather than recomputed.
    """
    return [
        _rail(m.key, m.score, m.confidence, m.counted, m.level, band)
        for m in measured
        if (band := audience.bands.get(m.key)) is not None
    ]


def fit_score(rails: list[Rail]) -> int:
    """0-100: how close the draft's tone sits to what this reader wants.

    A weighted average of how far each dimension missed its band, turned the
    right way up. Dimensions Jev was unsure about sit it out rather than
    dragging an invented number into the total.
    """
    counted = [rail for rail in rails if rail.counted]
    if not counted:
        return 0
    total_weight = sum(rail.weight for rail in counted)
    penalty = sum(rail.weight * min(rail.miss, 4.0) / 4.0 for rail in counted)
    return round(100 * (1 - penalty / total_weight))


def send_score(fit: int, findings: list[Finding]) -> int:
    """The headline number: fit, with the findings charged against it."""
    score = fit - sum(SEVERITY_COST[f.severity] for f in findings)
    if any(f.severity == "blocker" for f in findings):
        score = min(score, BLOCKER_CEILING)
    return max(0, min(100, score))


def verdict_for(score: int, findings: list[Finding], intent_confidence: float) -> str:
    if intent_confidence < INTENT_FLOOR:
        return UNCLEAR
    if any(f.severity == "blocker" for f in findings):
        return HOLD
    if score >= 85:
        return SEND
    if score >= 60:
        return TIGHTEN
    return REWRITE

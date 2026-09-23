"""The JSON the browser draws from.

Kept apart from the routes so the shapes live in one place: `web/src/api.ts`
mirrors exactly what these functions return, field for field.
"""

from __future__ import annotations

from .rap_sheet import Record
from .verdict import Charge, Verdict


def _spoken(name: str) -> str:
    """Archetypes are identifiers in Python and phrases in court."""
    return name.replace("_", " ")


def _level(score: float, legend: dict[int, str]) -> str:
    return legend.get(int(round(score)), "—")


def _measure(label: str, value: float, detail: str) -> dict:
    return {"label": label, "value": value, "detail": detail}


def _charge(charge: Charge, against: bool) -> dict:
    return {"label": charge.label, "probability": charge.probability, "against": against}


def as_payload(excuse: str, verdict: Verdict) -> dict:
    """Everything the front end needs, in the shape it draws."""
    ranked = sorted(verdict.archetype_probabilities.items(), key=lambda kv: kv[1], reverse=True)
    shown = [pair for pair in ranked[:5] if pair[1] >= 0.01] or ranked[:2]

    return {
        "excuse": excuse,
        "ruling": verdict.ruling,
        "headline": verdict.headline,
        "sentence": verdict.sentence,
        "mistrial": verdict.is_mistrial,
        "remarks": verdict.remarks,
        "confidence": verdict.believability_confidence,
        "measures": [
            _measure("believability", verdict.believability, f"{verdict.believability:.2f} / 4"),
            _measure("effort", verdict.effort, f"{verdict.effort:.2f} / 4"),
            _measure("drama", verdict.drama, f"{verdict.drama:.2f} / 4"),
            _measure(
                "survives up to",
                verdict.survives_up_to,
                _level(verdict.survives_up_to, verdict.survival_legend),
            ),
        ],
        "charges": (
            [_charge(c, True) for c in verdict.aggravating]
            + [_charge(c, False) for c in verdict.mitigating]
        ),
        "archetype": {
            "name": _spoken(verdict.archetype),
            "confidence": verdict.archetype_confidence,
            "ranked": [
                {
                    "name": _spoken(name),
                    "probability": probability,
                    "chosen": name == verdict.archetype,
                }
                for name, probability in shown
            ],
        },
    }


def record_payload(records: list[Record], stats: dict) -> dict:
    """The last twenty hearings, newest first, plus the running tally."""
    return {
        "hearings": [
            {
                "when": r.when,
                "excuse": r.excuse,
                "ruling": r.ruling,
                "archetype": _spoken(r.archetype),
                "believability": r.believability,
            }
            for r in records[-20:]
        ][::-1],
        "summary": {
            "hearings": stats.get("hearings", 0),
            "average_believability": stats.get("average_believability", 0.0),
            "signature_move": _spoken(stats["signature_move"][0]) if stats else None,
        },
    }

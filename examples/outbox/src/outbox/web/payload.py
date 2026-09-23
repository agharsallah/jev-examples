"""What the browser receives, and the way back from it.

`payload` is everything the front end draws, in the shape it draws it; the
TypeScript types in `web/src/api.ts` mirror it field for field. `rebuild` is
the return trip: a previous read's measurements turned back into a Review so
the verdict can be re-run for someone else.
"""

from __future__ import annotations

from .. import audience as audiences
from ..review import PROBE_LABELS, Finding, Review, rails_against, top_probe
from ..samples import SAMPLES
from .schemas import Measurement


def desk_config() -> dict:
    """The readers on offer and the drafts to try, for the empty state."""
    return {
        "audiences": [
            {
                "key": a.key,
                "label": a.label,
                "wants": a.wants,
                "bands": {
                    key: {"low": band.low, "high": band.high, "weight": band.weight}
                    for key, band in a.bands.items()
                },
            }
            for a in audiences.AUDIENCES.values()
        ],
        "samples": [
            {"draft": s.text, "to": s.to, "goal": s.goal, "channel": s.channel}
            for s in SAMPLES
        ],
    }


def _sentences(review: Review) -> list[dict]:
    marked = []
    for sentence in review.sentences:
        top = top_probe(sentence)
        marked.append(
            {
                "start": sentence.start,
                "end": sentence.end,
                "text": sentence.text,
                "probe": top,
                "label": PROBE_LABELS.get(top or "", ""),
                "probability": sentence.probes.get(top or "", 0.0),
                "probes": {
                    name: round(value, 3)
                    for name, value in sorted(sentence.probes.items(), key=lambda kv: -kv[1])
                },
            }
        )
    return marked


def _finding(f: Finding, *, rounded: bool) -> dict:
    return {
        "key": f.key,
        "severity": f.severity,
        "title": f.title,
        "fix": f.fix,
        "value": round(f.value, 3) if rounded else f.value,
        "strength": round(f.strength, 3) if rounded else f.strength,
    }


def _measurement(review: Review) -> dict:
    """Handed straight back on a reader change, so the browser never has to
    keep two copies of the truth. Unrounded, so a rescore sees what Jev said."""
    return {
        "draft": review.draft,
        "intent": review.intent,
        "intent_confidence": review.intent_confidence,
        "intent_ranked": review.intent_ranked,
        "risk": review.risk,
        "risk_confidence": review.risk_confidence,
        "rails": [
            {
                "key": r.key,
                "score": r.score,
                "confidence": r.confidence,
                "level": r.level,
                "counted": r.counted,
            }
            for r in review.rails
        ],
        "findings": [_finding(f, rounded=False) for f in review.findings],
    }


def payload(review: Review, *, rescored: bool = False) -> dict:
    """Everything the front end draws, in the shape it draws it."""
    return {
        "draft": review.draft,
        "verdict": review.verdict,
        "blurb": review.blurb,
        "sendScore": review.send_score,
        "fit": review.fit,
        "rescored": rescored,
        "audience": {
            "key": review.audience.key,
            "label": review.audience.label,
            "wants": review.audience.wants,
        },
        "intent": {
            "choice": review.intent,
            "confidence": review.intent_confidence,
            "ranked": [
                {"name": name, "probability": probability}
                for name, probability in review.intent_ranked[:4]
                if probability >= 0.01
            ],
        },
        "risk": {"choice": review.risk, "confidence": review.risk_confidence},
        "rails": [
            {
                "key": rail.key,
                "label": rail.label,
                "score": rail.score,
                "confidence": rail.confidence,
                "low": rail.low,
                "high": rail.high,
                "weight": rail.weight,
                "miss": round(rail.miss, 2),
                "counted": rail.counted,
                "level": rail.level,
                "verdict": rail.verdict,
            }
            for rail in review.rails
        ],
        "findings": [_finding(f, rounded=True) for f in review.findings],
        "sentences": _sentences(review),
        "cost": {
            "requests": review.requests_made,
            "questions": review.questions_asked,
            "inputTokens": review.input_tokens,
            "outputTokens": review.output_tokens,
        },
        "measurement": _measurement(review),
    }


def rebuild(measurement: Measurement, reader: audiences.Audience) -> Review:
    """Put a Review back together from a previous read's measurements.

    The verdict fields are left blank on purpose: `rescore` fills them in, and
    nothing between here and there should be reading them.
    """
    return Review(
        draft=measurement.draft,
        audience=reader,
        verdict="",
        blurb="",
        fit=0,
        send_score=0,
        intent=measurement.intent,
        intent_confidence=measurement.intent_confidence,
        intent_ranked=[tuple(pair) for pair in measurement.intent_ranked],
        risk=measurement.risk,
        risk_confidence=measurement.risk_confidence,
        rails=rails_against(measurement.rails, reader),
        findings=[Finding(**f.model_dump()) for f in measurement.findings],
    )

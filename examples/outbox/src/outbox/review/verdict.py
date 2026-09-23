"""One response in, one verdict out -- and the same again for another reader."""

from __future__ import annotations

from ..audience import Audience
from .findings import findings_for
from .model import VERDICT_BLURB, Review
from .scoring import fit_score, rails_against, rails_for, send_score, verdict_for


def assess(answers, audience: Audience, draft: str) -> Review:
    """Turn one System One response into a verdict for one reader."""
    intent = answers["intent"]
    risk = answers["biggest_risk"]

    findings = findings_for(answers, intent.choice)
    rails = rails_for(answers, audience)
    fit = fit_score(rails)
    score = send_score(fit, findings)
    verdict = verdict_for(score, findings, float(intent.confidence))

    return Review(
        draft=draft,
        audience=audience,
        verdict=verdict,
        blurb=VERDICT_BLURB[verdict],
        fit=fit,
        send_score=score,
        intent=intent.choice,
        intent_confidence=float(intent.confidence),
        intent_ranked=sorted(intent.probabilities.items(), key=lambda kv: -kv[1]),
        risk=risk.choice,
        risk_confidence=float(risk.confidence),
        rails=rails,
        findings=findings,
    )


def rescore(review: Review, audience: Audience) -> Review:
    """Re-run the verdict for a different reader, without asking Jev again.

    The scores did not change; what the reader wants did. This is the line the
    whole example is drawn around, so it is one function and no I/O.
    """
    rails = rails_against(review.rails, audience)
    fit = fit_score(rails)
    score = send_score(fit, review.findings)
    verdict = verdict_for(score, review.findings, review.intent_confidence)
    return Review(
        **{
            **review.__dict__,
            "audience": audience,
            "rails": rails,
            "fit": fit,
            "send_score": score,
            "verdict": verdict,
            "blurb": VERDICT_BLURB[verdict],
        }
    )

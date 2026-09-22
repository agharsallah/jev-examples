"""The desk, in a browser.

Two endpoints worth noticing. `/api/read` does what the CLI does: one request
to Jev, then a second for the sentences, then ordinary Python. `/api/rescore`
does not call Jev at all -- it takes the measurements from a review that has
already happened and re-runs the verdict for a different reader. That is the
whole argument of the example, wired to a row of buttons: the model measured
the draft once, and changing who is reading it is a code decision.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import audience as audiences
from .desk import DeskError
from .review import (
    PROBE_LABELS,
    PROBE_THRESHOLDS,
    Finding,
    Rail,
    Review,
    rescore,
)
from .reviewer import Draft, review
from .samples import SAMPLES

STATIC = Path(__file__).parent / "static"

# Which highlight wins when a sentence trips more than one probe.
PROBE_ORDER = ["sensitive", "barbed", "ambiguous", "hedged", "carries_the_ask", "cuttable"]


class ReadRequest(BaseModel):
    draft: str = Field(min_length=1, max_length=8000)
    to: str | None = Field(default=None, max_length=200)
    goal: str | None = Field(default=None, max_length=400)
    channel: str | None = Field(default=None, max_length=40)
    audience: str | None = None
    model: str | None = None
    deep: bool = True


class RailIn(BaseModel):
    """One measured dimension, as it came back from a previous read."""

    key: str
    score: float
    confidence: float
    level: str
    counted: bool


class FindingIn(BaseModel):
    key: str
    severity: str
    title: str
    fix: str
    value: float
    strength: float


class Measurement(BaseModel):
    """Everything Jev said about a draft, with none of the interpretation.

    The browser hands this back when the reader changes. Nothing in it depends
    on who the draft is for, which is exactly why it does not need asking again.
    """

    draft: str
    intent: str
    intent_confidence: float
    intent_ranked: list[tuple[str, float]]
    risk: str
    risk_confidence: float
    rails: list[RailIn]
    findings: list[FindingIn]


class RescoreRequest(BaseModel):
    measurement: Measurement
    audience: str


def _sentence_payload(review: Review) -> list[dict]:
    marked = []
    for sentence in review.sentences:
        flags = sentence.flagged(PROBE_THRESHOLDS)
        top = next((p for p in PROBE_ORDER if p in flags), None)
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
        "findings": [
            {
                "key": f.key,
                "severity": f.severity,
                "title": f.title,
                "fix": f.fix,
                "value": round(f.value, 3),
                "strength": round(f.strength, 3),
            }
            for f in review.findings
        ],
        "sentences": _sentence_payload(review),
        "cost": {
            "requests": review.requests_made,
            "questions": review.questions_asked,
            "inputTokens": review.input_tokens,
            "outputTokens": review.output_tokens,
        },
        # Handed straight back on a reader change, so the browser never has to
        # keep two copies of the truth.
        "measurement": {
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
            "findings": [
                {
                    "key": f.key,
                    "severity": f.severity,
                    "title": f.title,
                    "fix": f.fix,
                    "value": f.value,
                    "strength": f.strength,
                }
                for f in review.findings
            ],
        },
    }


def _rebuild(measurement: Measurement, reader: audiences.Audience) -> Review:
    """Put a Review back together from a previous read's measurements."""
    rails = [
        Rail(
            key=rail.key,
            label=rail.key.replace("_", " "),
            score=rail.score,
            confidence=rail.confidence,
            low=band.low,
            high=band.high,
            weight=band.weight,
            miss=band.miss(rail.score),
            counted=rail.counted,
            level=rail.level,
        )
        for rail in measurement.rails
        if (band := reader.bands.get(rail.key)) is not None
    ]
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
        rails=rails,
        findings=[Finding(**f.model_dump()) for f in measurement.findings],
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Outbox", docs_url=None, redoc_url=None)

    @app.get("/api/desk")
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
                {
                    "draft": s.text,
                    "to": s.to,
                    "goal": s.goal,
                    "channel": s.channel,
                }
                for s in SAMPLES
            ],
        }

    @app.post("/api/read")
    def read(request: ReadRequest) -> JSONResponse:
        draft = Draft(
            text=request.draft.strip(),
            to=request.to,
            goal=request.goal,
            channel=request.channel,
        )
        try:
            result = review(
                draft,
                audience_key=request.audience,
                model=request.model,
                deep=request.deep,
            )
        except DeskError as error:
            # The desk's own failures are already phrased for a person.
            return JSONResponse({"error": str(error)}, status_code=502)
        return JSONResponse(payload(result))

    @app.post("/api/rescore")
    def rescore_for(request: RescoreRequest) -> JSONResponse:
        """A different reader for the same draft. No model call happens here."""
        reader = audiences.resolve(request.audience)
        rebuilt = _rebuild(request.measurement, reader)
        return JSONResponse(payload(rescore(rebuilt, reader), rescored=True))

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()

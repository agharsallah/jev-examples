"""The courtroom, served over HTTP.

The browser gets the theatre; this module does exactly what the CLI does --
one request to Jev, then `deliberate` -- and hands the result over as JSON.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import rap_sheet
from .questions import excuse_docket
from .tribunal import TribunalError, hear_case
from .verdict import Verdict, deliberate

STATIC = Path(__file__).parent / "static"


class Plea(BaseModel):
    excuse: str = Field(min_length=1, max_length=2000)
    context: str | None = Field(default=None, max_length=500)
    audience: str | None = Field(default=None, max_length=200)
    model: str | None = None
    keep: bool = True


def _level(score: float, legend: dict[int, str]) -> str:
    return legend.get(int(round(score)), "—")


def _measure(label: str, value: float, detail: str) -> dict:
    return {"label": label, "value": value, "detail": detail}


def _charge(charge, against: bool) -> dict:
    return {"label": charge.label, "probability": charge.probability, "against": against}


def as_payload(excuse: str, verdict: Verdict) -> dict:
    """Everything the front end needs, in the shape it draws."""
    ranked = sorted(
        verdict.archetype_probabilities.items(), key=lambda kv: kv[1], reverse=True
    )
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
            "name": verdict.archetype.replace("_", " "),
            "confidence": verdict.archetype_confidence,
            "ranked": [
                {
                    "name": name.replace("_", " "),
                    "probability": probability,
                    "chosen": name == verdict.archetype,
                }
                for name, probability in shown
            ],
        },
    }


def create_app() -> FastAPI:
    app = FastAPI(title="The Excuse Tribunal", docs_url=None, redoc_url=None)

    @app.post("/api/judge")
    def judge(plea: Plea) -> JSONResponse:
        text = plea.excuse.strip()
        state = {"excuse": text}
        if plea.context:
            state["what_was_expected"] = plea.context
        if plea.audience:
            state["told_to"] = plea.audience

        try:
            response = hear_case(state, excuse_docket(), model=plea.model)
        except TribunalError as error:
            # The court's own failures are phrased for a human, so pass them through.
            return JSONResponse({"error": str(error)}, status_code=502)

        verdict = deliberate(response.answers)
        if plea.keep:
            rap_sheet.record("excuse", text, verdict)
        return JSONResponse(as_payload(text, verdict))

    @app.get("/api/record")
    def record() -> dict:
        records = rap_sheet.history()
        stats = rap_sheet.summary(records)
        return {
            "hearings": [
                {
                    "when": r.when,
                    "excuse": r.excuse,
                    "ruling": r.ruling,
                    "archetype": r.archetype.replace("_", " "),
                    "believability": r.believability,
                }
                for r in records[-20:]
            ][::-1],
            "summary": {
                "hearings": stats.get("hearings", 0),
                "average_believability": stats.get("average_believability", 0.0),
                "signature_move": stats["signature_move"][0].replace("_", " ") if stats else None,
            },
        }

    @app.delete("/api/record")
    def expunge() -> dict:
        if rap_sheet.RAP_SHEET.exists():
            rap_sheet.RAP_SHEET.unlink()
        return {"expunged": True}

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()

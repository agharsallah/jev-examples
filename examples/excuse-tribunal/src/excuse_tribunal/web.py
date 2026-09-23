"""The courtroom, served over HTTP.

The browser gets the theatre; this module does exactly what the CLI does --
one request to Jev, then `deliberate` -- and hands the result over as JSON,
in the shapes `payload.py` defines. The page itself is static: HTML, CSS split
by concern under `static/css/`, and ES modules compiled from `web/src` into
`static/js/`.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import rap_sheet
from .payload import as_payload, record_payload
from .questions import excuse_docket
from .tribunal import TribunalError, hear_case
from .verdict import deliberate

STATIC = Path(__file__).parent / "static"


class Plea(BaseModel):
    excuse: str = Field(min_length=1, max_length=2000)
    context: str | None = Field(default=None, max_length=500)
    audience: str | None = Field(default=None, max_length=200)
    model: str | None = None
    keep: bool = True


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
        return record_payload(records, rap_sheet.summary(records))

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

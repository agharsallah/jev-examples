"""The routes. Each one is a few lines, because the work lives elsewhere."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import audience as audiences
from ..desk import DeskError
from ..review import rescore
from ..reviewer import Draft, review
from .payload import desk_config, payload, rebuild
from .schemas import ReadRequest, RescoreRequest

# index.html, the stylesheets under css/, and the compiled TypeScript under js/.
STATIC = Path(__file__).resolve().parent.parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="Outbox", docs_url=None, redoc_url=None)

    @app.get("/api/desk")
    def desk() -> dict:
        """The readers on offer and the drafts to try, for the empty state."""
        return desk_config()

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
        rebuilt = rebuild(request.measurement, reader)
        return JSONResponse(payload(rescore(rebuilt, reader), rescored=True))

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app

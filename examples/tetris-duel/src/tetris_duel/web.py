"""The match, served over HTTP.

The browser owns both wells: it draws them, runs the clock, and handles the
keyboard. It does not own the key. Every move the left-hand board makes is one
POST to here, which does exactly what the terminal match does -- one request to
Jev, then the pilot -- and hands the answer back as JSON.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .board import HEIGHT, SHAPES, WIDTH
from .duel import GameOver, as_payload, play_piece
from .engine import EngineError
from .pilot import DIFFICULTIES

STATIC = Path(__file__).parent / "static"


class Move(BaseModel):
    rows: list[str] = Field(min_length=HEIGHT, max_length=HEIGHT)
    piece: str = Field(min_length=1, max_length=1)
    next: str | None = Field(default=None, max_length=1)
    cleared: int = Field(default=0, ge=0)
    since_bar: int | None = Field(default=None, ge=0, le=999)
    difficulty: str | None = None
    model: str | None = None


def create_app() -> FastAPI:
    app = FastAPI(title="Jev vs You", docs_url=None, redoc_url=None)

    @app.get("/api/levels")
    def levels() -> dict:
        return {
            "levels": [
                {
                    "key": level.key,
                    "label": level.label,
                    "blurb": level.blurb,
                    "gravity_ms": level.gravity_ms,
                    "sees": level.detail,
                    "house_rules": level.house_rules,
                    "well_guard": level.well_guard,
                }
                for level in DIFFICULTIES
            ],
            "well": {"width": WIDTH, "height": HEIGHT},
            "pieces": SHAPES,
        }

    @app.post("/api/move")
    def move(request: Move) -> JSONResponse:
        if request.piece not in SHAPES:
            return JSONResponse({"error": f"no such piece: {request.piece}"}, status_code=422)
        try:
            decision, menu, level = play_piece(
                request.rows,
                request.piece,
                request.next,
                rows_cleared=request.cleared,
                level_key=request.difficulty,
                model=request.model,
                since_bar=request.since_bar,
            )
        except GameOver:
            return JSONResponse({"game_over": True})
        except ValueError as error:
            return JSONResponse({"error": str(error)}, status_code=422)
        except EngineError as error:
            # Jev's own failures are already phrased for a human, so pass them through.
            return JSONResponse({"error": str(error)}, status_code=502)

        return JSONResponse(as_payload(decision, menu, level))

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()

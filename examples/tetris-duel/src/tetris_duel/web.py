"""The match, served over HTTP.

The browser owns both wells: it draws them, runs the clock, and handles the
keyboard. It does not own the key. Every move a model makes is one POST to
here, which does exactly what the terminal match does -- ask the player, then
the pilot -- and hands the answer back as JSON. Which players sit at which well
is the page's choice, from whatever `players.installed()` finds.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .board import HEIGHT, SHAPES, WIDTH
from .duel import GameOver
from .engine import EngineError
from .payload import as_payload
from .players import Player, installed

STATIC = Path(__file__).parent / "static"


class Move(BaseModel):
    rows: list[str] = Field(min_length=HEIGHT, max_length=HEIGHT)
    piece: str = Field(min_length=1, max_length=1)
    next: str | None = Field(default=None, max_length=1)
    cleared: int = Field(default=0, ge=0)
    since_bar: int | None = Field(default=None, ge=0, le=999)
    difficulty: str | None = None
    model: str | None = None


def mover(play, take_model: bool = False):
    """The handler for one player: POST a well, get that player's move.

    Only Jev takes `model` from the request, where it names a hosted model. For a
    local player it would be a checkpoint to download, which is the server's call.
    """

    def move(request: Move) -> JSONResponse:
        if request.piece not in SHAPES:
            return JSONResponse({"error": f"no such piece: {request.piece}"}, status_code=422)
        try:
            decision, menu, level = play(
                request.rows,
                request.piece,
                request.next,
                rows_cleared=request.cleared,
                level_key=request.difficulty,
                model=request.model if take_model else None,
                since_bar=request.since_bar,
            )
        except GameOver:
            return JSONResponse({"game_over": True})
        except ValueError as error:
            return JSONResponse({"error": str(error)}, status_code=422)
        except EngineError as error:
            # The engines' own failures are already phrased for a human, so pass them through.
            return JSONResponse({"error": str(error)}, status_code=502)

        return JSONResponse(as_payload(decision, menu, level))

    return move


def create_app(players: dict[str, Player] | None = None) -> FastAPI:
    """One arcade for every installed player; the page picks who sits at each well.

    Each player answers on `/api/move/<key>`. `/api/setup` says who is installed,
    who cannot play right now and why, and each player's own difficulty ladder.
    """
    seats = players if players is not None else installed()
    app = FastAPI(title="Tetris duel", docs_url=None, redoc_url=None)

    @app.get("/api/setup")
    def setup() -> dict:
        return {
            "players": [
                {
                    "key": player.key,
                    "name": player.name,
                    "about": player.about,
                    "blocked": player.blocked(),
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
                        for level in player.levels
                    ],
                }
                for player in seats.values()
            ],
            "well": {"width": WIDTH, "height": HEIGHT},
            "pieces": SHAPES,
        }

    movers = {key: mover(player.play, take_model=key == "jev") for key, player in seats.items()}

    @app.post("/api/move/{key}")
    def move(key: str, request: Move) -> JSONResponse:
        if key not in movers:
            return JSONResponse({"error": f"no such player: {key}"}, status_code=404)
        return movers[key](request)

    @app.post("/api/warm/{key}")
    def warm(key: str) -> JSONResponse:
        """Load a slow player before its first piece, so the match does not start on a stall."""
        player = seats.get(key)
        if player is None:
            return JSONResponse({"error": f"no such player: {key}"}, status_code=404)
        try:
            if player.warm:
                player.warm()
        except EngineError as error:
            return JSONResponse({"error": str(error)}, status_code=502)
        return JSONResponse({"ready": True})

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()

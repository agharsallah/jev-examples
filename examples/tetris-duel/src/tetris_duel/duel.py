"""One falling piece, start to finish, for any player.

Every player goes through the same steps: read the well, number every legal
landing, pick the slot worth defending, ask, and let the house rules in
`pilot.py` turn the answers into a move. Only the asking differs between
models, so that is the one thing a player supplies: an `Asker`. Jev's is in
`jev.py`; other packages bring their own.

`payload.py` turns the move into what a scoreboard draws, and `selfplay.py`
plays whole matches with it.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from .board import Grid, Landing, landings, read_grid, slot_column
from .pilot import Decision, Difficulty, decide


class GameOver(Exception):
    """The piece has nowhere legal to go."""


@dataclass(frozen=True)
class Turn:
    """Everything a player is asked about for one piece, worked out before it is asked."""

    grid: Grid
    piece: str
    next_piece: str | None
    rows_cleared: int
    since_bar: int | None
    level: Difficulty
    menu: dict[str, Landing]  # every legal landing, by the spot name the answers use
    slot: int | None  # the column the slot guard defends, on the tiers that have one
    model: str | None


@dataclass(frozen=True)
class Reply:
    """A player's answers, in the shape `pilot.decide` reads, and what they cost."""

    answers: Mapping[str, Any]  # landing, danger, clear_now, mood, and keep_the_slot
    model: str
    usage: dict


class Asker(Protocol):
    """The one part of a player that is not the shared harness: how it is asked."""

    name: str

    def difficulty(self, key: str | None) -> Difficulty: ...

    def ask(self, turn: Turn) -> Reply: ...


def menu(grid: Grid, piece: str) -> dict[str, Landing]:
    """Every legal landing, numbered in board order, so every player sees the same menu."""
    options = landings(grid, piece)
    if not options:
        raise GameOver(f"the {piece} piece has nowhere to land")
    return {f"spot_{i + 1}": landing for i, landing in enumerate(options)}


def play(
    asker: Asker,
    rows: list[str],
    piece: str,
    next_piece: str | None = None,
    rows_cleared: int = 0,
    level_key: str | None = None,
    model: str | None = None,
    since_bar: int | None = None,
) -> tuple[Decision, dict[str, Landing], Difficulty]:
    """Ask a player where this piece goes, and let the house rules have the last word."""
    level = asker.difficulty(level_key)
    grid = read_grid(rows)
    by_spot = menu(grid, piece)
    # Only the tier that defends a slot pays for the question about one.
    slot = slot_column(grid) if level.well_guard else None
    turn = Turn(grid, piece, next_piece, rows_cleared, since_bar, level, by_spot, slot, model)

    started = time.perf_counter()
    reply = asker.ask(turn)
    usage = {**reply.usage, "ms": round((time.perf_counter() - started) * 1000)}

    decision = decide(
        by_spot, reply.answers, level, model=reply.model, usage=usage, slot=slot, who=asker.name
    )
    return decision, by_spot, level

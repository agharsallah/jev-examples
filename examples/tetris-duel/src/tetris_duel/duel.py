"""One falling piece, start to finish.

The web app and the terminal both come through here: build the menu of legal
landings, ask Jev the docket, and let the pilot turn the answers into a move.
`payload.py` turns the move into what a scoreboard draws, and `selfplay.py`
plays whole matches with it.
"""

from __future__ import annotations

from .board import Grid, Landing, landings, read_grid, slot_column
from .engine import ask
from .pilot import Decision, Difficulty, decide, difficulty
from .questions import describe, move_docket, slot_question, well_state


class GameOver(Exception):
    """The piece has nowhere legal to go."""


def menu_for(
    grid: Grid, piece: str, level: Difficulty, next_piece: str | None = None
) -> tuple[dict[str, Landing], dict]:
    """Every legal landing, numbered, plus the version Jev is shown."""
    options = landings(grid, piece)
    if not options:
        raise GameOver(f"the {piece} piece has nowhere to land")
    by_spot = {f"spot_{i + 1}": landing for i, landing in enumerate(options)}
    shown = {
        spot: describe(landing, level.detail, next_piece) for spot, landing in by_spot.items()
    }
    return by_spot, shown


def play_piece(
    rows: list[str],
    piece: str,
    next_piece: str | None = None,
    rows_cleared: int = 0,
    level_key: str | None = None,
    model: str | None = None,
    since_bar: int | None = None,
) -> tuple[Decision, dict[str, Landing], Difficulty]:
    """Ask Jev where this piece goes, and let the house rules have the last word."""
    level = difficulty(level_key)
    grid = read_grid(rows)
    by_spot, shown = menu_for(grid, piece, level, next_piece)

    # Only the tier that defends a slot pays for the question about one.
    slot = slot_column(grid) if level.well_guard else None
    response = ask(
        well_state(grid, piece, next_piece, rows_cleared, level.detail),
        move_docket(shown, slot_question(grid, slot, since_bar) if slot is not None else None),
        model=model,
    )
    decision = decide(
        by_spot,
        response.answers,
        level,
        model=response.model,
        usage={
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
        slot=slot,
    )
    return decision, by_spot, level


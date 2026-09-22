"""One falling piece, start to finish.

The web app and the terminal both come through here: build the menu of legal
landings, ask Jev the docket, let the pilot turn the answers into a move, and
hand back something a scoreboard can draw.
"""

from __future__ import annotations

import random

from .board import Grid, Landing, landings, read_grid, settle
from .engine import ask
from .pilot import Decision, Difficulty, decide, difficulty
from .questions import describe, move_docket, well_state

# Jev picks the mood; the phrasing is ours. Selecting a line beats generating
# one -- it keeps the commentary in the same typed world as everything else.
CHEERS = {
    "cruising": ["All calm down here!", "Nice and tidy.", "Easy money.", "Barely breaking a sweat."],
    "tidying_up": ["Smoothing out that step.", "Just a spot of housekeeping.", "Filling in the dent."],
    "digging_out": ["Digging back down to those gaps!", "Spade work.", "Excavation underway."],
    "stacking_dangerously": ["Ooh, that is getting tall...", "Careful now!", "Running out of room!"],
    "setting_up_a_big_clear": ["Something big is brewing!", "Holding out for the long bar.", "Loading up!"],
    "improvising": ["No good options — making the best of it.", "Every choice costs something here.", "Improvising!"],
}


class GameOver(Exception):
    """The piece has nowhere legal to go."""


def menu_for(grid: Grid, piece: str, level: Difficulty) -> tuple[dict[str, Landing], dict]:
    """Every legal landing, numbered, plus the version Jev is shown."""
    options = landings(grid, piece)
    if not options:
        raise GameOver(f"the {piece} piece has nowhere to land")
    by_spot = {f"spot_{i + 1}": landing for i, landing in enumerate(options)}
    shown = {spot: describe(landing, level.detail) for spot, landing in by_spot.items()}
    return by_spot, shown


def play_piece(
    rows: list[str],
    piece: str,
    next_piece: str | None = None,
    rows_cleared: int = 0,
    level_key: str | None = None,
    model: str | None = None,
) -> tuple[Decision, dict[str, Landing], Difficulty]:
    """Ask Jev where this piece goes, and let the house rules have the last word."""
    level = difficulty(level_key)
    grid = read_grid(rows)
    by_spot, shown = menu_for(grid, piece, level)

    response = ask(
        well_state(grid, piece, next_piece, rows_cleared),
        move_docket(shown),
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
    )
    return decision, by_spot, level


def cheer(mood: str, rng: random.Random | None = None) -> str:
    lines = CHEERS.get(mood, CHEERS["cruising"])
    return (rng or random).choice(lines)


def as_payload(
    decision: Decision,
    menu: dict[str, Landing],
    level: Difficulty,
    shown: int = 6,
) -> dict:
    """Everything the scoreboard draws, in the shape it draws it."""
    ranked = sorted(
        menu.items(),
        key=lambda item: decision.probabilities.get(item[0], 0.0),
        reverse=True,
    )
    options = [
        {
            "spot": spot,
            "where": landing.where(),
            "probability": decision.probabilities.get(spot, 0.0),
            "rows_cleared": landing.rows_cleared,
            "new_gaps": landing.new_gaps,
            "chosen": spot == decision.spot,
            "jev": spot == decision.picked_by_jev,
        }
        for spot, landing in ranked[:shown]
    ]
    if not any(option["chosen"] for option in options):  # an overruled underdog
        landing = menu[decision.spot]
        options.append(
            {
                "spot": decision.spot,
                "where": landing.where(),
                "probability": decision.probabilities.get(decision.spot, 0.0),
                "rows_cleared": landing.rows_cleared,
                "new_gaps": landing.new_gaps,
                "chosen": True,
                "jev": False,
            }
        )

    landing = decision.landing
    return {
        "piece": landing.piece,
        "rotation": landing.rotation,
        "cells": [[x, y] for x, y in landing.cells],
        "where": landing.where(),
        "rows_cleared": landing.rows_cleared,
        "new_gaps": landing.new_gaps,
        "menu_size": len(menu),
        "options": options,
        "confidence": decision.confidence,
        "torn": decision.torn,
        "sure": decision.sure,
        "column": min(x for x, _ in landing.cells),
        "landing_row": min(y for _, y in landing.cells),
        "danger": {"value": decision.danger, "level": decision.danger_level},
        "clear_now": decision.clear_now,
        "holding_a_well": decision.holding_a_well,
        "mood": {"key": decision.mood, "line": cheer(decision.mood)},
        "overruled": decision.overruled,
        "note": decision.note,
        "difficulty": {"key": level.key, "label": level.label, "gravity_ms": level.gravity_ms},
        "model": decision.model,
        "usage": decision.usage,
    }


def next_well(rows: list[str], cells: list[list[int]]) -> tuple[list[str], int]:
    """Lock a move into a well and clear what it completes. Used by the terminal match."""
    grid, cleared = settle(read_grid(rows), tuple((x, y) for x, y in cells))
    return list(grid), cleared


def topped_out(rows: list[str], limit: int = 2) -> bool:
    """True once anything has reached the top few rows of the well."""
    return any("#" in row for row in read_grid(rows)[:limit])

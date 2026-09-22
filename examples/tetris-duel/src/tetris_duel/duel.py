"""One falling piece, start to finish.

The web app and the terminal both come through here: build the menu of legal
landings, ask Jev the docket, let the pilot turn the answers into a move, and
hand back something a scoreboard can draw.
"""

from __future__ import annotations

import random
import time
from collections.abc import Iterator
from dataclasses import dataclass, field

from .board import Grid, Landing, landings, read_grid, settle, slot_column
from .engine import ask
from .pilot import Decision, Difficulty, decide, difficulty
from .questions import describe, move_docket, slot_question, well_state

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
        "mood": {"key": decision.mood, "line": cheer(decision.mood)},
        "overruled": decision.overruled,
        "note": decision.note,
        "guarding": None if decision.guarding is None else decision.guarding + 1,
        "keep_slot": decision.keep_slot,
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


# ------------------------------------------------------------------ self play
#
# The scoring the browser uses, in one place, so a terminal match and a
# benchmark are playing the same game as the arcade.

LINE_SCORES = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}


@dataclass
class Tally:
    """How a self-played match went."""

    level: str
    score: int = 0
    lines: int = 0
    pieces: int = 0
    clears: dict[int, int] = field(default_factory=dict)
    tokens: int = 0
    hard_drops: int = 0
    overruled: int = 0
    seconds: float = 0.0
    topped_out: bool = False

    @property
    def level_number(self) -> int:
        return self.lines // 10 + 1

    @property
    def tetrises(self) -> int:
        return self.clears.get(4, 0)

    @property
    def seconds_per_piece(self) -> float:
        return self.seconds / self.pieces if self.pieces else 0.0

    def record(self, payload: dict, cleared: int) -> None:
        self.pieces += 1
        self.lines += cleared
        self.score += LINE_SCORES[cleared] * self.level_number
        self.tokens += payload["usage"].get("input_tokens", 0)
        self.hard_drops += bool(payload["sure"])
        self.overruled += bool(payload["overruled"])
        if cleared:
            self.clears[cleared] = self.clears.get(cleared, 0) + 1


def bag(rng: random.Random) -> Iterator[str]:
    """The standard seven-bag: every piece once, then shuffle again."""
    from .board import PIECES

    while True:
        pieces = list(PIECES)
        rng.shuffle(pieces)
        yield from pieces


def self_play(
    level_key: str,
    seed: int | None = None,
    pieces: int = 40,
    model: str | None = None,
) -> Iterator[tuple[list[str], dict, Tally]]:
    """Play a well on its own, yielding after every piece.

    The same seed deals the same pieces to every difficulty, so two runs differ
    only in what Jev was told and what the house rules did with the answer.
    """
    from .board import empty_grid

    rng = random.Random(seed)
    upcoming = bag(rng)
    rows = list(empty_grid())
    tally = Tally(level=level_key)
    piece = next(upcoming)
    since_bar = 0  # pieces dealt since the last straight bar
    started = time.perf_counter()

    for _ in range(pieces):
        following = next(upcoming)
        try:
            decision, menu, level = play_piece(
                rows,
                piece,
                following,
                rows_cleared=tally.lines,
                level_key=level_key,
                model=model,
                since_bar=since_bar,
            )
        except GameOver:
            tally.topped_out = True
            tally.seconds = time.perf_counter() - started
            return
        payload = as_payload(decision, menu, level)
        rows, cleared = next_well(rows, payload["cells"])
        tally.seconds = time.perf_counter() - started
        tally.record(payload, cleared)
        yield rows, payload, tally
        since_bar = 0 if piece == "I" else since_bar + 1
        piece = following

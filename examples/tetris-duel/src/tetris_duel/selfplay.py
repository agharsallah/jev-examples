"""Whole matches with nobody at the keyboard, for `watch`, `bench` and `versus`.

The same seed deals the same pieces as the arcade, and the scoring is the
arcade's, so a terminal match and a benchmark are playing the browser's game.
"""

from __future__ import annotations

import random
import time
from collections.abc import Iterator
from dataclasses import dataclass, field

from .board import read_grid, settle
from .duel import GameOver, play_piece
from .payload import as_payload


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
    play=None,
) -> Iterator[tuple[list[str], dict, Tally]]:
    """Play a well on its own, yielding after every piece.

    The same seed deals the same pieces to every difficulty, so two runs differ
    only in what Jev was told and what the house rules did with the answer.
    `play` swaps in another player with the same signature as `play_piece`.
    """
    from .board import empty_grid

    play = play or play_piece
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
            decision, menu, level = play(
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

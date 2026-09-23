"""The menu: every distinct place the falling piece could come to rest.

Nothing in here talks to a model. This is the mechanical part -- rotate, drop,
clear, count -- that turns a well and a piece into a list of legal landings,
each carrying the facts the questions are phrased from. Picking one off the
menu is the judgment, and that is the model's part.
"""

from __future__ import annotations

from dataclasses import dataclass

from .pieces import PIECES, Cells, rotation_name
from .well import (
    HEIGHT,
    WIDTH,
    Grid,
    buried_gaps,
    hard_drop,
    heights,
    roughness,
    settle,
    tucked_under,
)


@dataclass(frozen=True)
class Landing:
    """One legal place the falling piece could end up, and the well it leaves behind."""

    piece: str
    rotation: int
    cells: Cells
    after: Grid
    rows_cleared: int
    new_gaps: int
    tucked: int
    flush: bool
    gaps_after: int
    tallest_after: int
    roughness_after: int

    @property
    def columns(self) -> tuple[int, int]:
        xs = [x for x, _ in self.cells]
        return min(xs), max(xs)

    @property
    def floor_gap(self) -> int:
        """How far the lowest block of the piece sits above the floor."""
        return HEIGHT - 1 - max(y for _, y in self.cells)

    @property
    def signature(self) -> Grid:
        return self.after

    def where(self) -> str:
        left, right = self.columns
        span = f"column {left + 1}" if left == right else f"columns {left + 1}-{right + 1}"
        rows = "row" if self.floor_gap == 1 else "rows"
        rest = "on the floor" if self.floor_gap == 0 else f"{self.floor_gap} {rows} above the floor"
        return f"{rotation_name(self.piece, self.rotation)}, {span}, lowest block {rest}"

    def fit(self) -> str:
        """How the piece sits on what is already there, as a player would say it."""
        if self.flush:
            note = "Sits flush: every part of the piece rests on the stack or the floor."
        else:
            cells = "cell" if self.tucked == 1 else "cells"
            note = (
                f"Bridges a dip and seals {self.tucked} empty {cells} underneath, "
                "which cannot be reached again until the rows above clear."
            )
        if self.rows_cleared:
            rows = "row" if self.rows_cleared == 1 else "rows"
            note += f" Completes {self.rows_cleared} {rows}."
        return note

    def shape(self) -> str:
        """What the stack looks like afterwards, in words rather than numbers."""
        tallest = self.tallest_after
        height = "low" if tallest <= 6 else "mid-height" if tallest <= 11 else "high"
        surface = (
            "even"
            if self.roughness_after <= 4
            else "a little uneven"
            if self.roughness_after <= 8
            else "ragged"
        )
        return f"Leaves the stack {height} and {surface}."


def landings(grid: Grid, piece: str) -> list[Landing]:
    """Every distinct landing for this piece, in left-to-right order.

    Two landings that leave exactly the same well are the same move as far as
    the game is concerned, so only the first is kept.
    """
    before_gaps = buried_gaps(grid)
    found: list[Landing] = []
    seen: set[Grid] = set()

    for rotation, cells in enumerate(PIECES[piece]):
        width = max(x for x, _ in cells) + 1
        for x in range(WIDTH - width + 1):
            landed = hard_drop(grid, cells, x)
            if landed is None:
                continue
            after, cleared = settle(grid, landed)
            if after in seen:
                continue
            seen.add(after)
            tucked = tucked_under(grid, landed)
            column_heights = heights(after)
            found.append(
                Landing(
                    piece=piece,
                    rotation=rotation,
                    cells=landed,
                    after=after,
                    rows_cleared=cleared,
                    new_gaps=max(0, buried_gaps(after) - before_gaps),
                    tucked=tucked,
                    flush=tucked == 0,
                    gaps_after=buried_gaps(after),
                    tallest_after=max(column_heights),
                    roughness_after=roughness(column_heights),
                )
            )

    found.sort(key=lambda landing: (landing.columns[0], landing.rotation))
    return found

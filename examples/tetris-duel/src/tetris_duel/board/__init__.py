"""The well, the seven pieces, and every place a piece could land.

Nothing in here talks to a model. This package does the mechanical work a
computer is good at -- rotate the piece, drop it, clear the rows, count what is
left -- and turns it into a menu of legal landings, plus the findings about the
ground that the questions are phrased from. Picking one off the menu is the
judgment, and that is the part the model does.

  pieces    the seven shapes, their rotations and their names
  well      the grid: read, measure, drop, settle
  reading   what the ground looks like, in words
  landing   the menu of legal landings
"""

from .landing import Landing, landings
from .pieces import PIECES, ROTATION_NAMES, SHAPES, Cells, rotation_name
from .reading import deep_slot, landmarks, prospects, row_targets, rows_waiting_on, slot_column
from .well import (
    EMPTY,
    FILLED,
    HEIGHT,
    WIDTH,
    Grid,
    art,
    buried_gaps,
    column_gaps,
    empty_grid,
    hard_drop,
    heights,
    read_grid,
    roughness,
    settle,
    supported,
    tucked_under,
)

__all__ = [
    "Cells",
    "EMPTY",
    "FILLED",
    "Grid",
    "HEIGHT",
    "Landing",
    "PIECES",
    "ROTATION_NAMES",
    "SHAPES",
    "WIDTH",
    "art",
    "buried_gaps",
    "column_gaps",
    "deep_slot",
    "empty_grid",
    "hard_drop",
    "heights",
    "landings",
    "landmarks",
    "prospects",
    "read_grid",
    "rotation_name",
    "roughness",
    "row_targets",
    "rows_waiting_on",
    "settle",
    "slot_column",
    "supported",
    "tucked_under",
]

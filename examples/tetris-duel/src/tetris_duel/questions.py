"""What Jev is asked, once per falling piece.

One request carries the whole docket: which landing to take, how much trouble
the well is in, whether clearing rows is worth more than staying flat, and what
the crowd should be told. Jev reads the well once and answers all of them in
parallel, so four questions cost barely more than one -- the speculative
fan-out pattern, applied to a falling block.
"""

from __future__ import annotations

from collections.abc import Mapping

from typesafe_sdk import Choice, Noul, NoulCriteria, Score

from .board import SHAPES, Grid, Landing, art, buried_gaps, heights, roughness

RULES = (
    "A tetris-style well, 10 columns wide and 20 rows tall. Pieces fall in and stack up. "
    "A row that fills completely is cleared and everything above it drops down; clearing "
    "several rows at once is worth far more than clearing them one at a time. The game "
    "ends when the stack reaches the top, so a low, flat, unbroken surface is what keeps "
    "it alive, and an empty cell with blocks on top of it is dead weight until the rows "
    "above it are cleared away."
)

LEGEND = (
    "'#' is a filled cell and '.' is empty. The first row shown is the top of the stack "
    "and the last row shown rests on the floor."
)

DANGER_LEVELS = [
    "Nearly empty. The stack is a thin, tidy layer along the floor.",
    "Comfortable. A low stack with a surface pieces drop into easily.",
    "Getting untidy. Uneven columns or a couple of buried gaps to dig out.",
    "Serious. A tall or badly broken stack with little room left to be fussy.",
    "Critical. The stack is near the top and the next bad drop ends the game.",
]

MOODS = {
    "cruising": "Low, flat stack. Nothing to worry about; the piece just needs a tidy home.",
    "tidying_up": "The surface has a step or a dent in it and this drop is smoothing it out.",
    "digging_out": "There are buried gaps under the stack, and the point of this drop "
    "is to work back down to them.",
    "stacking_dangerously": "The stack is tall or ragged and the well is running out of "
    "forgiving places to put a piece.",
    "setting_up_a_big_clear": "Rows are nearly complete, or a deep clean column is being "
    "held open for a vertical bar.",
    "improvising": "The piece fits nowhere pleasant, and every option on the menu costs something.",
}


def piece_card(name: str) -> dict:
    return {"name": f"{name} piece", "shape": SHAPES[name]}


def well_state(grid: Grid, piece: str, next_piece: str | None, rows_cleared: int) -> dict:
    """Everything Jev needs to see before it is asked anything."""
    column_heights = heights(grid)
    state = {
        "how_the_game_works": RULES,
        "the_well_right_now": {"rows": art(grid), "legend": LEGEND},
        "the_stack": {
            "column_heights_left_to_right": column_heights,
            "tallest_column": max(column_heights),
            "buried_gaps": buried_gaps(grid),
            "surface_roughness": roughness(column_heights),
            "rows_cleared_so_far": rows_cleared,
        },
        "falling_piece": piece_card(piece),
    }
    if next_piece:
        state["piece_after_this_one"] = piece_card(next_piece)
    return state


# --------------------------------------------------------- the menu of landings
#
# How much of each landing Jev is shown is the difficulty dial. `position` is a
# blind drop: it knows the shape of the well and where the piece would go, and
# nothing else. `board` adds the well the drop leaves behind. `full` adds the
# numbers a human player counts without noticing.


def describe(landing: Landing, detail: str) -> str | dict:
    where = landing.where()
    if detail == "position":
        return where

    card: dict = {"the_piece_lands": where, "the_well_afterwards": art(landing.after)}
    if detail == "full":
        card |= {
            "rows_cleared_by_this_drop": landing.rows_cleared,
            "new_gaps_buried_under_the_piece": landing.new_gaps,
            "buried_gaps_afterwards": landing.gaps_after,
            "tallest_column_afterwards": landing.tallest_after,
            "surface_roughness_afterwards": landing.roughness_after,
        }
    return card


PLACEMENT_QUESTION = (
    "Each option is a place this piece could be dropped. Pick the one that leaves the "
    "well in the best state for the pieces still to come: low and flat, with no new empty "
    "cells sealed under the piece and no deep narrow canyon that only a vertical bar can "
    "fill. Clear rows when the clearing does not wreck the shape of what is left behind, "
    "and take the safe, boring landing when the stack is getting tall."
)


def move_docket(menu: Mapping[str, str | dict]) -> dict:
    """The four questions asked about one falling piece."""
    return {
        "landing": Choice(instructions=PLACEMENT_QUESTION, criteria=dict(menu)),
        "danger": Score(
            instructions="How much trouble is the well in right now, before this piece lands?",
            criteria=DANGER_LEVELS,
        ),
        "clear_now": Noul(
            instructions=(
                "Clearing rows with this piece matters more than keeping the surface flat and open."
            ),
            criteria=NoulCriteria(
                true="Rows are nearly full, or the stack is high enough that clearing cannot wait",
                false="The stack is low and calm; shape and flatness are worth more "
                "than a row right now",
            ),
        ),
        "holding_a_well": Noul(
            instructions=(
                "The stack is keeping one clean, deep column open, the way a player does "
                "while waiting for a vertical bar to fill it."
            ),
        ),
        "mood": Choice(
            instructions="What is happening in this well, as a commentator would call it?",
            criteria=MOODS,
        ),
    }

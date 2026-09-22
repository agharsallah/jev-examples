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

from .board import (
    HEIGHT,
    SHAPES,
    Grid,
    Landing,
    art,
    heights,
    landmarks,
    prospects,
    row_targets,
    rows_waiting_on,
)

RULES = (
    "A tetris-style well, 10 columns wide and 20 rows tall. Pieces fall in and stack up. "
    "A row that fills completely is cleared and everything above it drops down; clearing "
    "several rows at once is worth far more than clearing them one at a time. The game "
    "ends when the stack reaches the top, so a low, flat, unbroken surface is what keeps "
    "it alive, and an empty cell with blocks on top of it is dead weight until the rows "
    "above it are cleared away. Pieces are dealt in bags of seven, one of each shape, so "
    "only one piece in seven is the straight bar, and a dozen pieces can go by between one "
    "bar and the next. A gap that only a standing bar can fill is a bet on that wait: "
    "worth making while the stack is low, and a way to lose while it is high."
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


def well_state(
    grid: Grid,
    piece: str,
    next_piece: str | None,
    rows_cleared: int,
    detail: str = "board",
) -> dict:
    """Everything Jev needs to see before it is asked anything.

    The counting, measuring and comparing all happen in `board.py`; what goes
    into the state is the finding, in words. Jev reads language far better than
    it reads arithmetic, and anything it does not need for this decision is left
    out rather than sent along as background.
    """
    state = {
        "how_the_game_works": RULES,
        "the_well_right_now": {"rows": art(grid), "legend": LEGEND},
        "falling_piece": piece_card(piece),
    }
    if next_piece:
        state["piece_after_this_one"] = piece_card(next_piece)
    if detail in ("fit", "insight"):
        state["what_the_ground_looks_like"] = landmarks(grid)
    if detail == "insight":
        targets = row_targets(grid)
        if targets:
            state["rows_close_to_completing"] = targets
        state["rows_cleared_so_far"] = rows_cleared
    return state


# ---------------------------------------------------------- the menu of landings
#
# How much of each landing Jev is shown is the difficulty dial, and every tier
# above the first is something code worked out and then phrased, never a raw
# number for Jev to do arithmetic on.
#
#   position  where the piece would come to rest, and nothing else
#   board     ...plus a picture of the well it would leave behind
#   fit       ...plus how the piece sits on what is already there
#   insight   ...plus what the next piece could do afterwards


def follow_up(after: Grid, next_piece: str) -> str:
    """What the piece after this one could do, once this landing has happened.

    Both plies are worked out in code, so the question for Jev stays "which of
    these do I want" rather than "imagine the well, then imagine it again".
    """
    flush, best_clear, spots = prospects(after, next_piece)
    if not spots:
        return f"The {next_piece} would have nowhere left to go: this drop ends the game."
    if flush == 0:
        room = "nowhere clean to go — every landing would seal cells underneath"
    elif flush == 1:
        room = f"exactly one clean landing left out of {spots}"
    else:
        room = f"{flush} clean landings out of {spots}"
    if best_clear:
        rows = "row" if best_clear == 1 else "rows"
        return (
            f"The {next_piece} would then have {room}, and the best of them "
            f"completes {best_clear} {rows}."
        )
    return f"The {next_piece} would then have {room}, none of them completing a row."


def describe(landing: Landing, detail: str, next_piece: str | None = None) -> str | dict:
    where = landing.where()
    if detail == "position":
        return where

    card: dict = {"the_piece_lands": where, "the_well_afterwards": art(landing.after)}
    if detail in ("fit", "insight"):
        card["how_it_sits"] = landing.fit()
        card["what_it_leaves"] = landing.shape()
    if detail == "insight" and next_piece:
        card["then_the_next_piece"] = follow_up(landing.after, next_piece)
    return card



PLACEMENT_QUESTION = (
    "Each option is a place this piece could be dropped. Pick the one that leaves the well "
    "in the best state for the pieces still to come. A landing that seals empty cells under "
    "the piece is worse than one that sits flush on what is already there, even when it "
    "looks tidier. Keeping the stack low and the surface even is worth more than clearing a "
    "single row early on, and four rows taken at once are worth far more than four rows "
    "taken one at a time. Clear rows when the stack is getting tall, or when clearing does "
    "not spoil the shape of what is left behind."
)


def slot_question(grid: Grid, column: int, since_bar: int | None = None) -> Noul:
    """Whether to keep one named column open for a four-row clear.

    Naming the column, its depth and the rows already waiting on it turns a
    question about a plan into a question about a fact on the board. Asking
    "is the stack holding a well open?" makes Jev guess at intent, and the
    answers sit near 0.5, which is no answer at all.
    """
    column_heights = heights(grid)
    neighbours = [
        column_heights[x] for x in (column - 1, column + 1) if 0 <= x < len(column_heights)
    ]
    depth = min(neighbours) - column_heights[column] if neighbours else 0
    waiting = rows_waiting_on(grid, column)

    bar = {
        "how_often_one_is_dealt": (
            "one piece in seven: every bag of seven holds exactly one straight bar"
        )
    }
    if since_bar is not None:
        bar["pieces_since_the_last_one"] = since_bar
        bar["so_far_this_wait"] = (
            "a bar has not come up yet this game"
            if since_bar >= 12
            else "a bar is somewhere in the next few pieces"
            if since_bar >= 5
            else "a bar went past recently"
        )

    return Noul(
        instructions={
            "the_slot": {
                "column": column + 1,
                "how_deep_it_sits": (
                    f"{depth} rows below the columns beside it"
                    if depth > 0
                    else "level with the columns beside it"
                    if depth == 0
                    else f"{-depth} rows above the columns beside it"
                ),
                "rows_already_complete_except_for_it": waiting,
                "how_tall_the_stack_is": f"{max(column_heights)} of {HEIGHT} rows",
                "only_a_straight_bar_reaches_the_bottom_of_it": depth >= 3,
            },
            "the_straight_bar": bar,
            "question": (
                "Is it worth leaving `the_slot` empty for now, and putting this piece "
                "somewhere else, so that a standing bar can drop into it later and clear "
                "several rows at once?"
            ),
        },
        criteria=NoulCriteria(
            true=(
                "There is room to keep building around the slot for as long as the wait "
                "for a bar might last"
            ),
            false=(
                "The stack is too tall, or too broken, to spend more pieces waiting: "
                "fill the slot and take whatever rows are available now"
            ),
        ),
    )


def move_docket(menu: Mapping[str, str | dict], slot: Noul | None = None) -> dict:
    """The questions asked about one falling piece, all in a single request."""
    docket = {
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
        "mood": Choice(
            instructions="What is happening in this well, as a commentator would call it?",
            criteria=MOODS,
        ),
    }
    if slot is not None:
        docket["keep_the_slot"] = slot
    return docket

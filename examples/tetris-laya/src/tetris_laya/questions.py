"""What Laya is asked, once per falling piece, and how it is made to fit.

The docket is the same one Jev gets -- where to land, how much trouble the well
is in, whether to clear now, the mood, and on Grandmaster whether to keep the
slot -- but Laya is a small encoder with a fixed budget, and three things about
it shape how the questions are put:

- Every question gets 256 tokens for its instructions and all of its options,
  and each option is cut at 48. A well can offer 34 landings, so the menu never
  fits in one question. It is split into heats that do fit, the heat winners
  go through to a final, and so on until one question holds the whole field.
  Laya still makes every pick; code only decides who is in which heat.
- The state is cut off once the sequence reaches 1024 tokens, so what the
  decision needs most goes first and the rules of the game go last.
- The model card warns that `score` has a position bias and `noul` can
  under-report "true". Both are asked as plain `choice` questions instead, and
  read back into the shape the house rules expect.
"""

from __future__ import annotations

from tetris_duel.board import HEIGHT, Grid, heights, rows_waiting_on
from tetris_duel.questions import DANGER_LEVELS, MOODS

# ------------------------------------------------------------------ the docket

HEAT_QUESTION = (
    "Which drop leaves the well best for the pieces to come? Flush beats sealing holes; "
    "several rows at once beat one."
)

YES, NO = "A", "B"


def yes_or_no(instructions: str, yes: str, no: str) -> dict:
    """A noul, asked as a two-way choice with neutral keys, as the model card suggests."""
    return {
        "type": "choice",
        "instructions": instructions,
        "criteria": {YES: f"yes: {yes}", NO: f"no: {no}"},
    }


DANGER_KEYS = ("empty", "comfortable", "untidy", "serious", "critical")


def side_questions(grid: Grid, slot: int | None, since_bar: int | None) -> dict:
    """Everything but the landing, asked once, alongside the first round of heats."""
    questions = {
        # A score on this checkpoint rarely picks its first level, so the rubric
        # is a choice, and code reads the expected level back off it.
        "danger": {
            "type": "choice",
            "instructions": "How much trouble is the well in right now?",
            "criteria": dict(zip(DANGER_KEYS, DANGER_LEVELS, strict=True)),
        },
        "clear_now": yes_or_no(
            "Should this piece clear rows now rather than keep the surface flat?",
            "rows are nearly full or the stack is high",
            "the stack is low and calm; shape matters more",
        ),
        "mood": {
            "type": "choice",
            "instructions": "What is happening in this well, as a commentator would say it?",
            "criteria": MOODS,
        },
    }
    if slot is not None:
        questions["keep_the_slot"] = slot_question(grid, slot, since_bar)
    return questions


def slot_question(grid: Grid, column: int, since_bar: int | None) -> dict:
    """Whether to keep one named column empty for a straight bar, in one sentence of facts."""
    column_heights = heights(grid)
    neighbours = [
        column_heights[x] for x in (column - 1, column + 1) if 0 <= x < len(column_heights)
    ]
    depth = max(0, min(neighbours) - column_heights[column]) if neighbours else 0
    waiting = rows_waiting_on(grid, column)
    wait = "" if since_bar is None else f" {since_bar} pieces since the last bar;"
    return yes_or_no(
        f"Keep column {column + 1} empty for a straight bar? It is {depth} deep, {waiting} rows "
        f"wait on it, the stack is {max(column_heights)} of {HEIGHT} tall;{wait} one piece in "
        "seven is a bar.",
        "there is room to keep building while waiting",
        "too tall or broken to wait: fill it",
    )


def heats(
    spots: list[str],
    texts: dict[str, str],
    budget: int,
    count,
    most: int = 8,
) -> list[list[str]]:
    """Split a round into questions that each fit Laya's option budget.

    Greedy and in menu order: code only decides who races whom, never who wins.
    A heat of one is a bye, and the runner meets the others in the next round.
    """
    room = budget - count(HEAT_QUESTION) - 8
    out: list[list[str]] = [[]]
    used = 0
    for spot in spots:
        cost = min(48, 1 + count(f"{spot}: {texts[spot]}"))
        if out[-1] and (used + cost > room or len(out[-1]) >= most):
            out.append([])
            used = 0
        out[-1].append(spot)
        used += cost
    return out


def heat(spots: list[str], texts: dict[str, str]) -> dict:
    return {
        "type": "choice",
        "instructions": HEAT_QUESTION,
        "criteria": {spot: texts[spot] for spot in spots},
    }

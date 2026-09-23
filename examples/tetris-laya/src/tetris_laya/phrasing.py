"""What Laya reads: the state, most important first, and each landing in one line.

Jev gets a paragraph per landing. Laya's options share a 256-token budget and
its state is cut off at 1024 tokens, so the findings `tetris_duel.board` works
out are said here in as few tokens as still read as English.
"""

from __future__ import annotations

from tetris_duel.board import Grid, Landing, art, landmarks, prospects, rotation_name, row_targets

RULES = (
    "Tetris: rows that fill completely clear, several at once score far more, and the game "
    "ends when the stack reaches the top. Keep it low, flat and free of covered holes."
)

LEGEND = "'#' is filled, '.' is empty; the last row is the floor."


def well_state(
    grid: Grid,
    piece: str,
    next_piece: str | None,
    rows_cleared: int,
    detail: str,
) -> dict:
    """What Laya reads before every question, most important first."""
    state: dict = {
        "falling_piece": piece,
        "the_well": art(grid),
        "legend": LEGEND,
    }
    if next_piece:
        state["next_piece"] = next_piece
    if detail in ("fit", "insight"):
        state["the_ground"] = landmarks(grid)
    if detail == "insight":
        targets = row_targets(grid)
        if targets:
            state["rows_close_to_completing"] = targets
        state["rows_cleared_so_far"] = rows_cleared
    state["rules"] = RULES
    return state


# ---------------------------------------------------------- one landing, briefly
#
# Jev gets a paragraph per landing. Laya gets a line: the same findings from
# board.py, said in as few tokens as still reads as English.


def where(landing: Landing) -> str:
    left, right = landing.columns
    span = f"column {left + 1}" if left == right else f"columns {left + 1}-{right + 1}"
    rest = "on the floor" if landing.floor_gap == 0 else f"{landing.floor_gap} up"
    return f"{rotation_name(landing.piece, landing.rotation)}, {span}, {rest}"


def fit(landing: Landing) -> str:
    note = "flush" if landing.flush else f"seals {landing.tucked} holes"
    if landing.rows_cleared:
        rows = "row" if landing.rows_cleared == 1 else "rows"
        note += f", clears {landing.rows_cleared} {rows}"
    return note


def shape(landing: Landing) -> str:
    tallest = landing.tallest_after
    height = "low" if tallest <= 6 else "mid" if tallest <= 11 else "high"
    surface = (
        "even"
        if landing.roughness_after <= 4
        else "bumpy"
        if landing.roughness_after <= 8
        else "ragged"
    )
    return f"leaves it {height} and {surface}"


def then(landing: Landing, next_piece: str) -> str:
    flush, best_clear, spots = prospects(landing.after, next_piece)
    if not spots:
        return f"then {next_piece} has nowhere to go"
    note = f"then {next_piece} has {flush} clean spots"
    if best_clear:
        note += f", can clear {best_clear}"
    return note


def describe(landing: Landing, detail: str, next_piece: str | None = None) -> str:
    parts = [where(landing)]
    if detail in ("fit", "insight"):
        parts.append(fit(landing))
    if detail != "position":
        parts.append(shape(landing))
    if detail == "insight" and next_piece:
        parts.append(then(landing, next_piece))
    return "; ".join(parts)

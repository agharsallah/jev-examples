"""What a player would notice about the ground, worked out here and said in words.

Jev reads language far better than it reads arithmetic, so the counting and the
comparing happen in this module and only the findings are sent: the slot worth
keeping open, the rows nearly done, the shelves and cliffs, and what the next
piece could do on a well that does not exist yet.
"""

from __future__ import annotations

from .pieces import PIECES
from .well import EMPTY, HEIGHT, WIDTH, Grid, column_gaps, hard_drop, heights, tucked_under


def deep_slot(column_heights: list[int], depth: int = 3) -> int | None:
    """The column of a single-wide slot that only a standing bar can fill."""
    best, best_depth = None, depth - 1
    for x, height in enumerate(column_heights):
        left = column_heights[x - 1] if x > 0 else HEIGHT
        right = column_heights[x + 1] if x < WIDTH - 1 else HEIGHT
        drop = min(left, right) - height
        if drop > best_depth:
            best, best_depth = x, drop
    return best


def slot_column(grid: Grid) -> int:
    """The column worth keeping empty, so a standing bar can take four rows at once.

    A slot that already exists wins; otherwise it is always the right-hand edge.
    Picking the emptiest column instead sounds cleverer and plays worse: the
    answer moves as the stack grows, the plan changes with it, and no column is
    ever left alone long enough to become a well.
    """
    existing = deep_slot(heights(grid))
    return existing if existing is not None else WIDTH - 1


def rows_waiting_on(grid: Grid, column: int) -> int:
    """Rows that are already complete except for this one column."""
    return sum(
        1
        for y in range(HEIGHT)
        if grid[y][column] == EMPTY
        and all(grid[y][x] != EMPTY for x in range(WIDTH) if x != column)
    )


def _run_note(column_heights: list[int]) -> str | None:
    """The widest level shelf on the surface, if there is one worth naming."""
    best_start = best_len = 0
    start = 0
    for x in range(1, WIDTH + 1):
        if x == WIDTH or column_heights[x] != column_heights[start]:
            if x - start > best_len:
                best_start, best_len = start, x - start
            start = x
    if best_len < 3:
        return None
    end = best_start + best_len
    return f"columns {best_start + 1}-{end} are level: a flat shelf {best_len} wide."


def landmarks(grid: Grid) -> list[str]:
    """What a player would notice about the ground, said in words rather than numbers.

    Jev reads language far better than it reads arithmetic, so the counting and
    the comparing happen here and only the findings are sent.
    """
    column_heights = heights(grid)
    notes: list[str] = []

    tallest = max(column_heights)
    if tallest == 0:
        return ["The well is empty: every column is clear down to the floor."]
    lowest = min(column_heights)
    notes.append(
        f"The stack is {'low' if tallest <= 6 else 'mid-height' if tallest <= 11 else 'high'}: "
        f"its tallest column reaches {tallest} of the 20 rows, its shortest {lowest}."
    )

    shelf = _run_note(column_heights)
    if shelf:
        notes.append(shelf.capitalize())

    slot = deep_slot(column_heights)
    if slot is not None:
        left = column_heights[slot - 1] if slot > 0 else HEIGHT
        right = column_heights[slot + 1] if slot < WIDTH - 1 else HEIGHT
        notes.append(
            f"Column {slot + 1} is a single-wide slot {min(left, right) - column_heights[slot]} "
            "deep: only a standing bar reaches the bottom of it."
        )

    buried = [(x, column_gaps(grid, x)) for x in range(WIDTH)]
    buried = [(x, n) for x, n in buried if n]
    if buried:
        where = ", ".join(f"column {x + 1}" for x, _ in buried[:4])
        total = sum(n for _, n in buried)
        notes.append(
            f"{total} cell{'s are' if total > 1 else ' is'} trapped under the stack "
            f"({where}); those rows cannot clear until the blocks above them go."
        )
    else:
        notes.append("Nothing is trapped under the stack: every empty cell is still reachable.")

    steps = [x for x in range(WIDTH - 1) if abs(column_heights[x] - column_heights[x + 1]) >= 3]
    if steps:
        where = ", ".join(f"between columns {x + 1} and {x + 2}" for x in steps[:3])
        notes.append(f"The surface has a cliff {where}.")

    return notes


def row_targets(grid: Grid, limit: int = 3) -> list[str]:
    """The rows closest to completing, and exactly what they are still missing."""
    out = []
    for y in range(HEIGHT):
        missing = [x for x in range(WIDTH) if grid[y][x] == EMPTY]
        if not missing or len(missing) > 3:
            continue
        where = ", ".join(str(x + 1) for x in missing)
        cells = "cell" if len(missing) == 1 else "cells"
        columns = "column" if len(missing) == 1 else "columns"
        out.append(
            f"The row {HEIGHT - y} up from the floor needs {len(missing)} more "
            f"{cells}, in {columns} {where}."
        )
        if len(out) == limit:
            break
    return out


def prospects(grid: Grid, piece: str) -> tuple[int, int, int]:
    """What the next piece could do on this well: (flush spots, best clear, spots).

    A cheap two-ply look: it only asks whether the piece could sit flush and how
    many rows it could take, which is all the follow-up question needs.
    """
    flush = best_clear = spots = 0
    for cells in PIECES[piece]:
        span = max(x for x, _ in cells) + 1
        for x in range(WIDTH - span + 1):
            landed = hard_drop(grid, cells, x)
            if landed is None:
                continue
            spots += 1
            if tucked_under(grid, landed) == 0:
                flush += 1
            filled = {(cx, cy) for cx, cy in landed}
            rows = sum(
                1
                for y in {cy for _, cy in landed}
                if all(grid[y][x2] != EMPTY or (x2, y) in filled for x2 in range(WIDTH))
            )
            best_clear = max(best_clear, rows)
    return flush, best_clear, spots

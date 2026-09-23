"""The well itself: reading it, measuring it, dropping a piece in and clearing rows.

Pure mechanics on an immutable grid -- a tuple of row strings, '#' filled and
'.' empty, top row first -- so every function here is safe to call on a
hypothetical well as freely as on the real one.
"""

from __future__ import annotations

from .pieces import Cells

WIDTH = 10


HEIGHT = 20


EMPTY = "."


FILLED = "#"


Grid = tuple[str, ...]


def read_grid(rows: list[str]) -> Grid:
    """Take whatever the browser sent and keep only what is filled and what is not."""
    if len(rows) != HEIGHT:
        raise ValueError(f"the well is {HEIGHT} rows tall, got {len(rows)}")
    out = []
    for row in rows:
        if len(row) != WIDTH:
            raise ValueError(f"the well is {WIDTH} columns wide, got a row of {len(row)}")
        out.append("".join(EMPTY if ch == EMPTY else FILLED for ch in row))
    return tuple(out)


def empty_grid() -> Grid:
    return tuple(EMPTY * WIDTH for _ in range(HEIGHT))


def heights(grid: Grid) -> list[int]:
    """How tall each column stands, measured up from the floor."""
    out = []
    for x in range(WIDTH):
        column = next((y for y in range(HEIGHT) if grid[y][x] != EMPTY), HEIGHT)
        out.append(HEIGHT - column)
    return out


def buried_gaps(grid: Grid) -> int:
    """Empty cells with something above them -- the holes you have to dig out."""
    total = 0
    for x in range(WIDTH):
        covered = False
        for y in range(HEIGHT):
            if grid[y][x] != EMPTY:
                covered = True
            elif covered:
                total += 1
    return total


def roughness(column_heights: list[int]) -> int:
    """Total step between neighbouring columns. Flat is 0."""
    return sum(abs(a - b) for a, b in zip(column_heights, column_heights[1:], strict=False))


def art(grid: Grid, headroom: int = 1) -> list[str]:
    """The well as rows of text, trimmed to the part that has anything in it."""
    top = next((y for y, row in enumerate(grid) if row != EMPTY * WIDTH), HEIGHT)
    start = max(0, min(top - headroom, HEIGHT - 1))
    return list(grid[start:])


def _fits(grid: Grid, cells: Cells, x: int, dy: int) -> bool:
    for cx, cy in cells:
        gx, gy = cx + x, cy + dy
        if gx < 0 or gx >= WIDTH or gy >= HEIGHT:
            return False
        if gy >= 0 and grid[gy][gx] != EMPTY:
            return False
    return True


def hard_drop(grid: Grid, cells: Cells, x: int) -> Cells | None:
    """Where the piece comes to rest in column offset `x`, or None if it cannot go there."""
    dy = -max(cy for _, cy in cells) - 1  # start entirely above the well
    if not _fits(grid, cells, x, dy):
        return None
    while _fits(grid, cells, x, dy + 1):
        dy += 1
    landed = tuple((cx + x, cy + dy) for cx, cy in cells)
    if any(gy < 0 for _, gy in landed):
        return None  # it would stick out of the top: that landing is not available
    return landed


def settle(grid: Grid, cells: Cells) -> tuple[Grid, int]:
    """Lock the piece in, clear any full rows, and report how many went."""
    rows = [list(row) for row in grid]
    for x, y in cells:
        rows[y][x] = FILLED
    kept = ["".join(row) for row in rows if EMPTY in row]
    cleared = HEIGHT - len(kept)
    return tuple([EMPTY * WIDTH] * cleared + kept), cleared


def column_gaps(grid: Grid, x: int) -> int:
    """Empty cells under the top of column `x`."""
    top = next((y for y in range(HEIGHT) if grid[y][x] != EMPTY), HEIGHT)
    return sum(1 for y in range(top, HEIGHT) if grid[y][x] == EMPTY)


def tucked_under(grid: Grid, cells: Cells) -> int:
    """Empty cells sealed directly beneath the piece when it lands.

    This is what a player means by "that one's going to cost me": the cells you
    can no longer reach without clearing the rows on top of them.
    """
    total = 0
    bottoms: dict[int, int] = {}
    for x, y in cells:
        bottoms[x] = max(bottoms.get(x, y), y)
    for x, bottom in bottoms.items():
        for y in range(bottom + 1, HEIGHT):
            if grid[y][x] != EMPTY:
                break
            total += 1
    return total


def supported(grid: Grid, cells: Cells) -> bool:
    """True when every column of the piece rests on the stack or the floor."""
    return tucked_under(grid, cells) == 0

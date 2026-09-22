"""The well, the seven pieces, and every place a piece could land.

Nothing in here talks to Jev. This module does the mechanical work a computer
is good at -- rotate the piece, drop it, clear the rows, count what is left --
and turns it into a menu of legal landings. Picking one off the menu is the
judgment, and that is the part Jev does.
"""

from __future__ import annotations

from dataclasses import dataclass

WIDTH = 10
HEIGHT = 20
EMPTY = "."
FILLED = "#"

# Each piece as it looks on screen, read top row first.
SHAPES: dict[str, list[str]] = {
    "I": ["####"],
    "O": ["##", "##"],
    "T": ["###", ".#."],
    "S": [".##", "##."],
    "Z": ["##.", ".##"],
    "J": ["#..", "###"],
    "L": ["..#", "###"],
}

Cells = tuple[tuple[int, int], ...]
Grid = tuple[str, ...]


def _cells(rows: list[str]) -> Cells:
    return tuple((x, y) for y, row in enumerate(rows) for x, ch in enumerate(row) if ch == "#")


def _normalize(cells: Cells) -> Cells:
    left = min(x for x, _ in cells)
    top = min(y for _, y in cells)
    return tuple(sorted((x - left, y - top) for x, y in cells))


def _turn(cells: Cells) -> Cells:
    """One quarter turn clockwise."""
    bottom = max(y for _, y in cells)
    return _normalize(tuple((bottom - y, x) for x, y in cells))


def _orientations(rows: list[str]) -> tuple[Cells, ...]:
    """The distinct rotations of a piece: four for T/J/L, two for I/S/Z, one for O."""
    seen: list[Cells] = []
    shape = _normalize(_cells(rows))
    for _ in range(4):
        if shape not in seen:
            seen.append(shape)
        shape = _turn(shape)
    return tuple(seen)


PIECES: dict[str, tuple[Cells, ...]] = {name: _orientations(rows) for name, rows in SHAPES.items()}

ROTATION_NAMES = {
    "I": ("flat", "upright"),
    "O": ("square",),
    "T": ("pointing down", "pointing left", "pointing up", "pointing right"),
    "S": ("flat", "upright"),
    "Z": ("flat", "upright"),
    "J": ("hook left", "hook up", "hook right", "hook down"),
    "L": ("hook right", "hook down", "hook left", "hook up"),
}


def rotation_name(piece: str, rotation: int) -> str:
    names = ROTATION_NAMES.get(piece, ())
    return names[rotation] if rotation < len(names) else f"rotation {rotation}"


# --------------------------------------------------------------------- the well


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


# --------------------------------------------------------------- the legal menu


@dataclass(frozen=True)
class Landing:
    """One legal place the falling piece could end up, and the well it leaves behind."""

    piece: str
    rotation: int
    cells: Cells
    after: Grid
    rows_cleared: int
    new_gaps: int
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
            column_heights = heights(after)
            found.append(
                Landing(
                    piece=piece,
                    rotation=rotation,
                    cells=landed,
                    after=after,
                    rows_cleared=cleared,
                    new_gaps=max(0, buried_gaps(after) - before_gaps),
                    gaps_after=buried_gaps(after),
                    tallest_after=max(column_heights),
                    roughness_after=roughness(column_heights),
                )
            )

    found.sort(key=lambda landing: (landing.columns[0], landing.rotation))
    return found

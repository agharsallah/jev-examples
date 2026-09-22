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

    steps = [
        x
        for x in range(WIDTH - 1)
        if abs(column_heights[x] - column_heights[x + 1]) >= 3
    ]
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
            "even" if self.roughness_after <= 4
            else "a little uneven" if self.roughness_after <= 8
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

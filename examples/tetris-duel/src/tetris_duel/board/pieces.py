"""The seven pieces, their rotations, and what a player calls each rotation."""

from __future__ import annotations

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

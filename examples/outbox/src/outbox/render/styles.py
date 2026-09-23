"""The palette and the shared console. Every glyph and colour lives here."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from ..review import HOLD, REWRITE, SEND, TIGHTEN, UNCLEAR

console = Console()

WIDTH = 26

VERDICT_STYLE = {
    SEND: "bold black on green",
    TIGHTEN: "bold black on yellow",
    REWRITE: "bold white on dark_orange3",
    HOLD: "bold white on red",
    UNCLEAR: "bold black on grey70",
}

SEVERITY_STYLE = {
    "blocker": ("!!", "bold red"),
    "major": ("!", "yellow"),
    "minor": ("·", "grey70"),
    "good": ("✓", "green"),
}

PROBE_STYLE = {
    "carries_the_ask": "bold underline cyan",
    "barbed": "bold red",
    "hedged": "yellow",
    "ambiguous": "magenta",
    "sensitive": "bold white on red",
    "cuttable": "dim strike",
}


def banner() -> None:
    console.print(
        Text.from_markup(
            "\n[bold]OUTBOX[/bold] [dim]· a second opinion before you hit send[/dim]\n"
        )
    )

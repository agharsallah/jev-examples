"""Terminal theatre for `duel watch`."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

BLOCKS = {".": "  ", "#": "██"}
DANGER_COLOURS = ["green", "green", "yellow", "orange3", "red"]


def banner() -> None:
    console.print(
        Text.from_markup(
            "\n[bold magenta]  ██[/bold magenta]\n"
            "[bold magenta] ████[/bold magenta]   [bold]JEV vs YOU[/bold]\n"
            "[bold magenta]  ██[/bold magenta]    "
            "[dim]a self-playing well · one API call per piece[/dim]\n"
        )
    )


def well(rows: list[str], title: str, subtitle: str = "") -> Panel:
    body = Text()
    for row in rows:
        body.append("".join(BLOCKS.get(cell, "  ") for cell in row), style="bright_cyan")
        body.append("\n")
    body.append("─" * (len(rows[0]) * 2), style="dim")
    return Panel(body, title=title, subtitle=subtitle, border_style="magenta", expand=False)


def reading(payload: dict) -> Panel:
    """What Jev said about this move."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim", justify="right")
    table.add_column()

    danger = payload["danger"]
    colour = DANGER_COLOURS[min(4, int(round(danger["value"])))]
    table.add_row("lands", payload["where"])
    table.add_row("from", f"{payload['menu_size']} legal landings")
    aside = "  (torn)" if payload["torn"] else ("  (sure — hard drop)" if payload["sure"] else "")
    table.add_row("confidence", f"{payload['confidence']:.0%}{aside}")
    table.add_row("danger", f"[{colour}]{danger['value']:.2f} / 4[/{colour}]  {danger['level']}")
    table.add_row("clear now", f"{payload['clear_now']:.0%}")
    table.add_row("holding a well", f"{payload['holding_a_well']:.0%}")
    mood = payload["mood"]
    table.add_row("mood", f"[bold]{mood['key'].replace('_', ' ')}[/bold] — {mood['line']}")

    bars = Table.grid(padding=(0, 1))
    bars.add_column(justify="right", style="dim")
    bars.add_column()
    bars.add_column()
    for option in payload["options"]:
        width = max(1, round(option["probability"] * 20))
        mark = "◀" if option["chosen"] else " "
        style = "bold magenta" if option["chosen"] else "dim"
        bars.add_row(
            f"{option['probability']:.0%}",
            Text("█" * width, style=style),
            Text(f"{option['where']} {mark}", style=style),
        )

    parts = [table, Text(), bars]
    if payload["overruled"]:
        parts += [Text(), Text(payload["note"], style="bold yellow")]
    return Panel(Group(*parts), border_style="cyan", title="what Jev said", expand=False)

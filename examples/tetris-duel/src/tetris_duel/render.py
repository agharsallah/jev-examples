"""Terminal theatre for `duel watch`."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

BLOCKS = {".": "  ", "#": "██"}
DANGER_COLOURS = ["green", "green", "yellow", "orange3", "red"]


def clock(seconds: float) -> str:
    """Seconds as a scoreboard reads them."""
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


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
    if payload.get("keep_slot") is not None:
        slot = payload["guarding"]
        held = f"  (holding column {slot})" if slot else ""
        table.add_row("keep the slot", f"{payload['keep_slot']:.0%}{held}")
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


def scoreline(label: str, tally, pieces: int) -> Text:
    """One line as a benchmark match finishes, so a long run shows its working."""
    ending = "topped out" if tally.topped_out else f"{tally.pieces} pieces"
    return Text.from_markup(
        f"[dim]·[/dim] [bold magenta]{label:<12}[/bold magenta] "
        f"[bold]{tally.score:>5}[/bold] points  "
        f"[dim]{tally.lines:>2} rows · {ending} · {clock(tally.seconds)} played[/dim]"
    )


def bench_table(results: list, levels: dict, pieces: int, games: int) -> Table:
    """The whole benchmark, one row per difficulty, averaged over its matches."""
    table = Table(
        title=f"{pieces} pieces per match, {games} match{'es' if games > 1 else ''} each, "
        "same seeds throughout",
        title_style="dim",
        border_style="magenta",
        header_style="bold",
    )
    table.add_column("difficulty")
    table.add_column("points", justify="right")
    table.add_column("rows", justify="right")
    table.add_column("clears", justify="left")
    table.add_column("survived", justify="right")
    table.add_column("tokens/piece", justify="right")
    table.add_column("sec/piece", justify="right")

    for key, level in levels.items():
        runs = [tally for tally in results if tally.level == key]
        if not runs:
            continue
        played = sum(tally.pieces for tally in runs) or 1
        counts = {n: sum(tally.clears.get(n, 0) for tally in runs) for n in (1, 2, 3, 4)}
        shape = " ".join(f"{n}×{counts[n]}" for n in (1, 2, 3, 4) if counts[n]) or "—"
        alive = sum(not tally.topped_out for tally in runs)
        table.add_row(
            level.label,
            f"[bold]{sum(t.score for t in runs) / len(runs):.0f}[/bold]",
            f"{sum(t.lines for t in runs) / len(runs):.1f}",
            shape,
            f"{alive}/{len(runs)}",
            f"{sum(t.tokens for t in runs) / played:.0f}",
            f"{sum(t.seconds for t in runs) / played:.1f}",
        )
    return table

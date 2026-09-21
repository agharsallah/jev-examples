"""Courtroom theatre, rendered with rich."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .verdict import RULINGS, Verdict

console = Console()

GAVEL = r"""
        __
   ____/  \____      THE EXCUSE TRIBUNAL
  |____________|     presided over by Jev
       |  |
       |__|          all rise
"""

RULING_STYLE = {
    RULINGS["guilty"]: "bold white on red",
    RULINGS["suspicion"]: "bold black on yellow",
    RULINGS["acquitted"]: "bold white on green",
    RULINGS["mistrial"]: "bold white on blue",
}


def banner() -> None:
    console.print(Text(GAVEL, style="bold yellow"))


def _bar(value: float, width: int = 24, style: str = "cyan") -> Text:
    filled = round(max(0.0, min(1.0, value)) * width)
    return Text("█" * filled, style=style) + Text("·" * (width - filled), style="dim")


def _scale(value: float, top: float, width: int = 24) -> Text:
    return _bar(value / top if top else 0.0, width)


def _level(score: float, legend: dict[int, str]) -> str:
    # The SDK hands back the legend keyed by level number, not by string.
    return legend.get(int(round(score)), "—")


def _findings(verdict: Verdict) -> Table:
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold", width=3)
    table.add_column()
    table.add_column(style="dim")
    for charge in verdict.aggravating:
        table.add_row("✗", Text(charge.label, style="red"), f"{charge.probability:.0%}")
    for charge in verdict.mitigating:
        table.add_row("✓", Text(charge.label, style="green"), f"{charge.probability:.0%}")
    if not verdict.aggravating and not verdict.mitigating:
        table.add_row(" ", Text("Nothing on the record either way.", style="dim"), "")
    return table


def _distribution(verdict: Verdict, limit: int = 4) -> Table:
    table = Table.grid(padding=(0, 1))
    table.add_column(style="dim", justify="right", width=18)
    table.add_column()
    table.add_column(style="dim", width=5)
    ranked = sorted(verdict.archetype_probabilities.items(), key=lambda kv: kv[1], reverse=True)
    # Options Jev ruled out entirely are noise; keep at least the top two.
    shown = [pair for pair in ranked[:limit] if pair[1] >= 0.01] or ranked[:2]
    for name, probability in shown:
        label = name.replace("_", " ")
        style = "magenta" if name == verdict.archetype else "dim magenta"
        table.add_row(label, _bar(probability, style=style), f"{probability:.0%}")
    return table


def _measures(verdict: Verdict) -> Table:
    table = Table.grid(padding=(0, 1))
    table.add_column(style="dim", justify="right", width=18)
    table.add_column()
    table.add_column(width=28)
    believability = f"{verdict.believability:.2f} / 4"
    table.add_row("believability", _scale(verdict.believability, 4.0), believability)
    table.add_row("effort", _scale(verdict.effort, 4.0), f"{verdict.effort:.2f} / 4")
    table.add_row("drama", _scale(verdict.drama, 4.0), f"{verdict.drama:.2f} / 4")
    table.add_row(
        "survives up to",
        _scale(verdict.survives_up_to, 4.0),
        Text(_level(verdict.survives_up_to, verdict.survival_legend), style="italic"),
    )
    return table


def verdict_report(excuse: str, verdict: Verdict) -> None:
    console.print(Panel(Text(excuse.strip(), style="italic"), title="the accused states",
                        border_style="dim", title_align="left"))

    body = Group(
        Text(verdict.headline, style="bold"),
        Text(""),
        _measures(verdict),
        Text(""),
        Text("reading of the charges", style="dim"),
        _findings(verdict),
        Text(""),
        Text(f"filed as: {verdict.archetype.replace('_', ' ')}"
             f"  (confidence {verdict.archetype_confidence:.0%})", style="dim"),
        _distribution(verdict),
    )
    console.print(Panel(body, title=verdict.ruling, title_align="left",
                        border_style=RULING_STYLE.get(verdict.ruling, "white").split()[-1]))

    for remark in verdict.remarks:
        console.print(Text(f"  the bench notes: {remark}", style="italic dim"))

    console.print()
    console.print(Text(" SENTENCE ", style=RULING_STYLE.get(verdict.ruling, "bold")),
                  Text(verdict.sentence, style="bold"))
    console.print(
        Text(f"  (believability confidence {verdict.believability_confidence:.0%})", style="dim")
    )


def rap_sheet_report(records, stats: dict) -> None:
    if not records:
        console.print(Text("No record. Either innocent or careful.", style="dim"))
        return

    table = Table(title="prior offences", title_style="bold yellow", border_style="dim")
    table.add_column("date", style="dim")
    table.add_column("statement", overflow="ellipsis", max_width=46)
    table.add_column("filed as", style="magenta")
    table.add_column("ruling")
    for entry in records[-12:]:
        table.add_row(entry.when[:10], entry.excuse, entry.archetype.replace("_", " "),
                      Text(entry.ruling, style=RULING_STYLE.get(entry.ruling, "white")))
    console.print(table)

    move, count = stats["signature_move"]
    console.print(
        Text(f"{stats['hearings']} hearings · average believability "
             f"{stats['average_believability']:.2f} / 4 · signature move: "
             f"{move.replace('_', ' ')} ({count}×)", style="dim")
    )

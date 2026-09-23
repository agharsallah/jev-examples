"""The shorter reports: consistency runs, a batch of drafts, the model list."""

from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..review import Review
from ..reviewer import Stability
from .styles import VERDICT_STYLE, console


def stability_report(stability: Stability) -> None:
    """What happened when the same draft was read several times over."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    for verdict, count in sorted(stability.verdicts.items(), key=lambda kv: -kv[1]):
        bar = "█" * count
        table.add_row(verdict, Text(f"{bar} {count}/{stability.runs}", style="cyan"))

    wobble = Table.grid(padding=(0, 2))
    wobble.add_column(style="dim")
    wobble.add_column(justify="right", style="dim")
    for name, spread in stability.wobbliest:
        wobble.add_row(name.replace("_", " "), f"±{spread:.02f}")

    settled = (
        Text("The desk says the same thing every time.", style="green")
        if stability.settled
        else Text("This draft sits on a line. Treat the verdict as a suggestion.", style="yellow")
    )
    console.print(
        Panel(
            Group(
                Text(f"{stability.runs} independent reads", style="bold"),
                Text(),
                table,
                Text(),
                Text(
                    f"send score {min(stability.send_scores)}-{max(stability.send_scores)}"
                    f"  (spread {stability.spread})",
                    style="dim",
                ),
                Text(),
                Text("least settled answers", style="dim"),
                wobble,
                Text(),
                settled,
            ),
            title="consistency",
            border_style="grey35",
            padding=(1, 2),
        )
    )


def batch_report(reviews: list[Review]) -> None:
    """Two lines per draft, so a pile of them still reads at any width."""
    for review in reviews:
        line = Text("  ")
        line.append(f" {review.verdict} ", style=VERDICT_STYLE[review.verdict])
        line.append(f"  {review.send_score:>3}/100", style="bold")
        line.append(f"  {review.intent}", style="cyan")
        line.append(f" · {review.risk.replace('_', ' ')}", style="magenta")
        line.append(f" · for {review.audience.label}", style="dim")
        console.print(line)
        snippet = review.draft.replace("\n", " ")
        room = max(40, console.width - 6)
        if len(snippet) > room:
            snippet = snippet[: room - 1] + "\u2026"
        console.print(Text(f"    {snippet}", style="dim"))
        console.print()

    console.print(
        Text(
            f" {len(reviews)} drafts · {sum(r.questions_asked for r in reviews)} questions"
            f" · {len(reviews)} concurrent requests · "
            f"{sum(r.input_tokens for r in reviews)} in / "
            f"{sum(r.output_tokens for r in reviews)} out",
            style="dim",
        )
    )


def models_report(models: list[tuple[str, str, str]]) -> None:
    table = Table(box=None, pad_edge=False)
    table.add_column("model", style="bold")
    table.add_column("released", style="dim")
    table.add_column("description")
    for name, released, description in models:
        table.add_row(name, released[:10], description)
    console.print(table)

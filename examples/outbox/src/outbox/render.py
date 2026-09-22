"""The desk, in a terminal.

Nothing here decides anything; it only draws what review.py already worked out.
The one interesting piece is `rail_bar`, which shows the band the audience
wants alongside where the draft actually landed -- the gap between those two is
the whole verdict.
"""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .review import HOLD, PROBE_LABELS, PROBE_THRESHOLDS, REWRITE, SEND, TIGHTEN, UNCLEAR, Review
from .reviewer import Stability

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

# The order highlights are applied in, so the worst one wins a sentence.
PROBE_ORDER = ["sensitive", "barbed", "ambiguous", "hedged", "carries_the_ask", "cuttable"]


def banner() -> None:
    console.print(
        Text.from_markup(
            "\n[bold]OUTBOX[/bold] [dim]· a second opinion before you hit send[/dim]\n"
        )
    )


def rail_bar(score: float, low: float, high: float, counted: bool) -> Text:
    """A 0-4 rail: the band this reader wants, and where the draft landed."""
    bar = Text()
    marker = round(score / 4 * (WIDTH - 1))
    lo, hi = round(low / 4 * (WIDTH - 1)), round(high / 4 * (WIDTH - 1))
    for cell in range(WIDTH):
        if cell == marker:
            bar.append("◆", style="bold white" if counted else "dim")
        elif lo <= cell <= hi:
            bar.append("─", style="green" if counted else "dim")
        else:
            bar.append("·", style="grey35")
    return bar


def _rails_table(review: Review) -> Table:
    table = Table.grid(padding=(0, 1))
    table.add_column(justify="right", style="bold")
    table.add_column()
    table.add_column(justify="right")
    table.add_column()
    for rail in review.rails:
        note = {
            "in band": Text("on target", style="green"),
            "too low": Text(f"too low for {review.audience.label}", style="yellow"),
            "too high": Text(f"too high for {review.audience.label}", style="yellow"),
            "unsure": Text(f"unscored · confidence {rail.confidence:.0%}", style="dim"),
        }[rail.verdict]
        table.add_row(
            rail.label,
            rail_bar(rail.score, rail.low, rail.high, rail.counted),
            Text(f"{rail.score:.2f}", style="white" if rail.counted else "dim"),
            note,
        )
    return table


def _findings_table(review: Review) -> Table:
    table = Table.grid(padding=(0, 1))
    table.add_column(width=2, justify="center")
    table.add_column()
    table.add_column(justify="right", style="dim")
    for finding in review.findings:
        glyph, style = SEVERITY_STYLE[finding.severity]
        body = Text(finding.title, style=style)
        if finding.fix:
            body.append(f"\n{finding.fix}", style="dim")
        table.add_row(Text(glyph, style=style), body, f"{finding.strength:.0%}")
    return table


def marked_draft(review: Review) -> Text:
    """The draft with each flagged sentence painted where Jev flagged it."""
    text = Text(review.draft, style="white")
    for sentence in review.sentences:
        flags = sentence.flagged(PROBE_THRESHOLDS)
        for probe in PROBE_ORDER:
            if probe in flags:
                text.stylize(PROBE_STYLE[probe], sentence.start, sentence.end)
                break
    return text


def _legend(review: Review) -> Text | None:
    used = {
        probe
        for sentence in review.sentences
        for probe in sentence.flagged(PROBE_THRESHOLDS)
    }
    if not used:
        return None
    legend = Text()
    for probe in PROBE_ORDER:
        if probe in used:
            if legend:
                legend.append("   ")
            legend.append("▌", style=PROBE_STYLE[probe])
            legend.append(f" {PROBE_LABELS[probe]}", style="dim")
    return legend


def report(review: Review) -> None:
    """The whole verdict, top to bottom."""
    header = Text()
    header.append(f" {review.verdict} ", style=VERDICT_STYLE[review.verdict])
    header.append(f"  {review.send_score}/100 ", style="bold")
    header.append(f"for {review.audience.label}", style="dim")

    intent = Text()
    intent.append(f"reads as a {review.intent.replace('_', ' ')}", style="cyan")
    intent.append(f" ({review.intent_confidence:.0%} confident)", style="dim")
    intent.append(f" · {review.risk.replace('_', ' ')}", style="magenta")
    intent.append(f" ({review.risk_confidence:.0%})", style="dim")

    fit = Text()
    fit.append(f"fit for {review.audience.label}: ", style="dim")
    fit.append(f"{review.fit}/100", style="bold")
    fit.append(f" · {review.audience.label} wants {review.audience.wants}", style="dim")

    blocks = [
        header,
        Text(review.blurb, style="italic dim"),
        Text(),
        intent,
        fit,
        Text(),
        _rails_table(review),
    ]
    if review.findings:
        blocks += [Text(), _findings_table(review)]
    if review.sentences:
        blocks += [Text(), marked_draft(review)]
        legend = _legend(review)
        if legend:
            blocks += [Text(), legend]

    console.print(Panel(Group(*blocks), border_style="grey35", padding=(1, 2)))
    console.print(
        Text(
            f" {review.questions_asked} questions in {review.requests_made} "
            f"request{'s' if review.requests_made > 1 else ''} · "
            f"{review.input_tokens} in / {review.output_tokens} out",
            style="dim",
        )
    )


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

"""The full report for one draft, top to bottom.

The one interesting piece is `rail_bar`, which shows the band the audience
wants alongside where the draft actually landed -- the gap between those two is
the whole verdict.
"""

from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..review import PROBE_LABELS, PROBE_ORDER, PROBE_THRESHOLDS, Review, top_probe
from .styles import PROBE_STYLE, SEVERITY_STYLE, VERDICT_STYLE, WIDTH, console


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
        probe = top_probe(sentence)
        if probe is not None:
            text.stylize(PROBE_STYLE[probe], sentence.start, sentence.end)
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

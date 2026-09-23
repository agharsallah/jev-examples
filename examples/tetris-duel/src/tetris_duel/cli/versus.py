"""Two players on the same pieces, side by side in the terminal."""

from __future__ import annotations

import random
from typing import Annotated

import typer
from rich.columns import Columns

from .. import render
from ..engine import EngineError
from ..selfplay import self_play
from .common import DEFAULT_LEVEL, check_levels, fail, levels_of, seat


def status_line(who: str, payload: dict | None, tally, done: bool) -> str:
    if payload is None:
        return f"[bold]{who}[/bold]  [dim]topped out before anything landed[/dim]"
    state = "[red]topped out[/red]" if done and tally.topped_out else ""
    aside = " · [yellow]overruled[/yellow]" if payload["overruled"] else ""
    tokens = payload["usage"].get("input_tokens", 0)
    return (
        f"[bold]{who}[/bold]  {payload['where']}  "
        f"[dim]{payload['confidence']:.0%} sure · {tokens} tokens{aside}[/dim] {state}"
    )


def versus(
    left: Annotated[str, typer.Option("--left", help="The left-hand player.")] = "jev",
    right: Annotated[str, typer.Option("--right", help="The right-hand player.")] = "laya",
    difficulty: Annotated[str, typer.Option("--difficulty", "-d", help="chill, steady, ruthless or grandmaster.")] = DEFAULT_LEVEL,
    pieces: Annotated[int, typer.Option("--pieces", "-n", help="How many pieces each.")] = 40,
    seed: Annotated[int | None, typer.Option("--seed", help="Fix the piece order.")] = None,
) -> None:
    """Watch two players play the same pieces side by side, in the terminal."""
    if left == right:
        fail("Pick two different players: the same one twice plays the same game twice.")
    seated = [seat(left), seat(right)]
    for who in seated:
        check_levels(who, [difficulty])
    title = f"vs {seated[1].name} · the same pieces, one well each"
    render.banner(seated[0].name, title)
    seed = seed if seed is not None else random.randrange(1_000_000)
    label = levels_of(seated[0])[difficulty].label

    # The same seed deals the same bag to both, so the two wells are the same game.
    matches = {who.name: self_play(difficulty, seed=seed, pieces=pieces, play=who.play) for who in seated}
    latest: dict[str, tuple] = {}
    done: set[str] = set()
    try:
        while len(done) < len(matches):
            for name, moves in matches.items():
                if name in done:
                    continue
                try:
                    latest[name] = next(moves)
                except StopIteration:
                    done.add(name)
            render.console.clear()
            render.banner(seated[0].name, title)
            wells, lines = [], []
            for name in matches:
                rows, payload, tally = latest.get(name, ([], None, None))
                if tally is None:
                    lines.append(status_line(name, None, None, True))
                    continue
                wells.append(
                    render.well(
                        rows[-16:],
                        title=f"[bold]{name}[/bold] · {tally.score} points · {tally.lines} rows · {tally.pieces}/{pieces}",
                        subtitle=f"{label} · {render.clock(tally.seconds)}",
                    )
                )
                lines.append(status_line(name, payload, tally, name in done))
            render.console.print(Columns(wells, padding=(0, 2)))
            for line in lines:
                render.console.print(line)
    except EngineError as error:
        fail(str(error))

    (a, b) = (who.name for who in seated)
    scores = {name: (latest[name][2].score if name in latest else 0) for name in matches}
    verdict = "A dead heat" if scores[a] == scores[b] else f"{max(scores, key=scores.get)} wins by {abs(scores[a] - scores[b])}"
    render.console.print(
        f"\n[bold magenta]{verdict}[/bold magenta]: {a} {scores[a]}, {b} {scores[b]}, "
        f"from the same {pieces} pieces [dim](seed {seed})[/dim].\n"
    )

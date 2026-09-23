"""Laya and Jev on the same pieces, side by side in the terminal."""

from __future__ import annotations

from typing import Annotated

import typer
from tetris_duel import render
from tetris_duel.engine import EngineError
from tetris_duel.selfplay import self_play

from ..levels import BY_KEY, DEFAULT
from ..play import play_piece
from .common import MODEL_HELP, check, fail, load_model, need_jev


def status_line(who: str, payload: dict | None, tally, done: bool) -> str:
    if payload is None:
        return f"[bold]{who}[/bold]  [dim]topped out before anything landed[/dim]"
    state = "[red]topped out[/red]" if done and tally.topped_out else ""
    aside = " · [yellow]overruled[/yellow]" if payload["overruled"] else ""
    return (
        f"[bold]{who}[/bold]  {payload['where']}  "
        f"[dim]{payload['confidence']:.0%} sure · {payload['usage'].get('input_tokens', 0)} tokens{aside}[/dim] {state}"
    )


def versus(
    difficulty: Annotated[
        str, typer.Option("--difficulty", "-d", help=f"One of: {', '.join(BY_KEY)}.")
    ] = DEFAULT,
    pieces: Annotated[int, typer.Option("--pieces", "-n", help="How many pieces each.")] = 40,
    seed: Annotated[int | None, typer.Option("--seed", help="Fix the piece order.")] = None,
    model: Annotated[str | None, typer.Option("--model", "-m", help=MODEL_HELP)] = None,
    jev_model: Annotated[
        str | None, typer.Option("--jev-model", help="Jev model, e.g. jev-1.13.0.")
    ] = None,
) -> None:
    """Watch Laya and Jev play the same pieces side by side, in the terminal."""
    import random

    from rich.columns import Columns
    from tetris_duel.duel import play_piece as jev_plays

    check([difficulty])
    need_jev()
    render.banner("Laya", "vs Jev · the same pieces, one well each")
    load_model(model)
    seed = seed if seed is not None else random.randrange(1_000_000)
    label = BY_KEY[difficulty].label

    # The same seed deals the same bag to both, so the two wells are the same game.
    players = {
        "Laya": self_play(difficulty, seed=seed, pieces=pieces, model=model, play=play_piece),
        "Jev": self_play(difficulty, seed=seed, pieces=pieces, model=jev_model, play=jev_plays),
    }
    latest: dict[str, tuple] = {}
    done: set[str] = set()
    try:
        while len(done) < len(players):
            for who, moves in players.items():
                if who in done:
                    continue
                try:
                    latest[who] = next(moves)
                except StopIteration:
                    done.add(who)
            render.console.clear()
            render.banner("Laya", "vs Jev · the same pieces, one well each")
            wells, lines = [], []
            for who in players:
                rows, payload, tally = latest.get(who, ([], None, None))
                if tally is None:
                    lines.append(status_line(who, None, None, True))
                    continue
                wells.append(
                    render.well(
                        rows[-16:],
                        title=f"[bold]{who}[/bold] · {tally.score} points · {tally.lines} rows · "
                        f"{tally.pieces}/{pieces}",
                        subtitle=f"{label} · {render.clock(tally.seconds)}",
                    )
                )
                lines.append(status_line(who, payload, tally, who in done))
            render.console.print(Columns(wells, padding=(0, 2)))
            for line in lines:
                render.console.print(line)
    except EngineError as error:
        fail(str(error))

    scores = {who: (latest[who][2].score if who in latest else 0) for who in players}
    laya, jev = scores["Laya"], scores["Jev"]
    verdict = (
        "A dead heat"
        if laya == jev
        else f"{'Laya' if laya > jev else 'Jev'} wins by {abs(laya - jev)}"
    )
    render.console.print(
        f"\n[bold magenta]{verdict}[/bold magenta]: Laya {laya}, Jev {jev}, "
        f"from the same {pieces} pieces [dim](seed {seed})[/dim].\n"
    )

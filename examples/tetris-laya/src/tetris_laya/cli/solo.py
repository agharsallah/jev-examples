"""Laya on its own: watch one match, bench the ladder, read the levels."""

from __future__ import annotations

from typing import Annotated

import typer
from tetris_duel import render
from tetris_duel.engine import EngineError
from tetris_duel.selfplay import self_play

from ..levels import BY_KEY, DEFAULT, LEVELS
from ..play import play_piece
from .common import MODEL_HELP, TAGLINE, check, fail, load_model


def watch(
    difficulty: Annotated[
        str, typer.Option("--difficulty", "-d", help=f"One of: {', '.join(BY_KEY)}.")
    ] = DEFAULT,
    pieces: Annotated[int, typer.Option("--pieces", "-n", help="How many pieces to play.")] = 40,
    seed: Annotated[int | None, typer.Option("--seed", help="Fix the piece order.")] = None,
    model: Annotated[str | None, typer.Option("--model", "-m", help=MODEL_HELP)] = None,
) -> None:
    """Watch Laya play in the terminal."""
    check([difficulty])
    render.banner("Laya", TAGLINE)
    load_model(model)
    tally = None
    try:
        for rows, payload, tally in self_play(
            difficulty, seed=seed, pieces=pieces, model=model, play=play_piece
        ):
            render.console.clear()
            render.banner("Laya", TAGLINE)
            render.console.print(
                render.well(
                    rows[-16:],
                    title=f"[bold]{tally.score}[/bold] points · {tally.lines} rows · "
                    f"piece {tally.pieces}/{pieces} · {render.clock(tally.seconds)}",
                    subtitle=f"{BY_KEY[difficulty].label} · next: {payload['piece']}",
                )
            )
            render.console.print(render.reading(payload, who="Laya"))
    except EngineError as error:
        fail(str(error))

    if tally is None:
        render.console.print("\n[bold red]Topped out[/bold red] before anything landed.")
        return
    if tally.topped_out:
        render.console.print("\n[bold red]Topped out.[/bold red] The well is full.")
    render.console.print(
        f"\n[bold magenta]{tally.score}[/bold magenta] points from [bold]{tally.lines}[/bold] rows "
        f"in [bold]{render.clock(tally.seconds)}[/bold] of play. "
        f"[dim]Play it yourself with `laya-duel serve`.[/dim]\n"
    )


def bench(
    difficulty: Annotated[
        list[str] | None,
        typer.Option("--difficulty", "-d", help="Repeatable; defaults to all of them."),
    ] = None,
    pieces: Annotated[int, typer.Option("--pieces", "-n", help="Pieces per match.")] = 40,
    games: Annotated[int, typer.Option("--games", "-g", help="Matches per difficulty.")] = 1,
    seed: Annotated[
        int, typer.Option("--seed", help="First seed; each match takes the next one.")
    ] = 1,
    model: Annotated[str | None, typer.Option("--model", "-m", help=MODEL_HELP)] = None,
) -> None:
    """Play the same pieces at every difficulty and print what each one scored.

    The seeds deal the same pieces as `duel bench`, so the two tables compare
    Laya and Jev on identical games.
    """
    keys = difficulty or list(BY_KEY)
    check(keys)
    render.banner("Laya", TAGLINE)
    load_model(model)
    results = []
    for key in keys:
        for game in range(games):
            tally = None
            with render.console.status(f"[magenta]{BY_KEY[key].label}[/magenta] match {game + 1}…"):
                try:
                    for move in self_play(
                        key, seed=seed + game, pieces=pieces, model=model, play=play_piece
                    ):
                        tally = move[2]
                except EngineError as error:
                    fail(str(error))
            if tally is not None:
                results.append(tally)
                render.console.print(render.scoreline(BY_KEY[key].label, tally, pieces))
    render.console.print(render.bench_table(results, BY_KEY, pieces, games))


def levels() -> None:
    """What each difficulty actually changes for Laya."""
    render.banner("Laya", TAGLINE)
    for level in LEVELS:
        render.console.print(f"[bold magenta]{level.label}[/bold magenta] [dim]({level.key})[/dim]")
        render.console.print(f"  {level.blurb}")
        rules = "on" if level.house_rules else "off"
        guard = " + slot guard" if level.well_guard else ""
        render.console.print(
            f"  [dim]laya sees: {level.detail} · house rules: {rules}{guard} · "
            f"gravity: {level.gravity_ms}ms[/dim]\n"
        )

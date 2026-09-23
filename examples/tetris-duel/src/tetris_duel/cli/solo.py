"""One player on its own: watch a match, bench the ladder, read the levels."""

from __future__ import annotations

from typing import Annotated

import typer

from .. import render
from ..engine import EngineError
from ..players import installed
from ..selfplay import self_play
from .common import DEFAULT_LEVEL, MODEL_HELP, PLAYER_HELP, check_levels, fail, levels_of, seat


def watch(
    player: Annotated[str, typer.Option("--player", "-P", help=PLAYER_HELP)] = "jev",
    difficulty: Annotated[str, typer.Option("--difficulty", "-d", help="chill, steady, ruthless or grandmaster.")] = DEFAULT_LEVEL,
    pieces: Annotated[int, typer.Option("--pieces", "-n", help="How many pieces to play.")] = 40,
    seed: Annotated[int | None, typer.Option("--seed", help="Fix the piece order.")] = None,
    model: Annotated[str | None, typer.Option("--model", "-m", help=MODEL_HELP)] = None,
) -> None:
    """Watch a player play alone in the terminal, one move per piece."""
    who = seat(player, model)
    check_levels(who, [difficulty])
    label = levels_of(who)[difficulty].label
    render.banner(who.name)
    tally = None
    try:
        for rows, payload, tally in self_play(difficulty, seed=seed, pieces=pieces, model=model, play=who.play):
            render.console.clear()
            render.banner(who.name)
            render.console.print(
                render.well(
                    rows[-16:],
                    title=f"[bold]{tally.score}[/bold] points · {tally.lines} rows · "
                    f"piece {tally.pieces}/{pieces} · {render.clock(tally.seconds)}",
                    subtitle=f"{label} · next: {payload['piece']}",
                )
            )
            render.console.print(render.reading(payload, who=who.name))
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
        f"[dim]Play it yourself with `duel serve`.[/dim]\n"
    )


def bench(
    player: Annotated[str, typer.Option("--player", "-P", help=PLAYER_HELP)] = "jev",
    difficulty: Annotated[list[str] | None, typer.Option("--difficulty", "-d", help="Repeatable; defaults to all of them.")] = None,
    pieces: Annotated[int, typer.Option("--pieces", "-n", help="Pieces per match.")] = 40,
    games: Annotated[int, typer.Option("--games", "-g", help="Matches per difficulty.")] = 1,
    seed: Annotated[int, typer.Option("--seed", help="First seed; each match takes the next one.")] = 1,
    model: Annotated[str | None, typer.Option("--model", "-m", help=MODEL_HELP)] = None,
) -> None:
    """Play the same pieces at every difficulty and print what each one scored.

    For Jev that is one request per piece, so `-n 40 -g 1` over four difficulties
    is 160 calls. Every difficulty, and every player, gets the same seeds, so two
    rows of the table differ only in who played and what they were told.
    """
    who = seat(player, model)
    ladder = levels_of(who)
    keys = difficulty or list(ladder)
    check_levels(who, keys)

    render.banner(who.name)
    results = []
    for key in keys:
        for game in range(games):
            tally = None
            with render.console.status(f"[magenta]{ladder[key].label}[/magenta] match {game + 1}…"):
                try:
                    for move in self_play(key, seed=seed + game, pieces=pieces, model=model, play=who.play):
                        tally = move[2]
                except EngineError as error:
                    fail(str(error))
            if tally is not None:
                results.append(tally)
                render.console.print(render.scoreline(ladder[key].label, tally, pieces))
    render.console.print(render.bench_table(results, ladder, pieces, games))


def levels(
    player: Annotated[str | None, typer.Option("--player", "-P", help="Just this player; all of them by default.")] = None,
) -> None:
    """What each difficulty actually changes, for every installed player."""
    players = installed()
    if player is not None and player not in players:
        fail(f"No such player: {player}. Installed: {', '.join(players)}.")
    render.banner()
    for who in players.values():
        if player is not None and who.key != player:
            continue
        render.console.print(f"[bold cyan]{who.name}[/bold cyan]\n")
        for level in who.levels:
            render.console.print(f"[bold magenta]{level.label}[/bold magenta] [dim]({level.key})[/dim]")
            render.console.print(f"  {level.blurb}")
            rules = "on" if level.house_rules else "off"
            guard = " + slot guard" if level.well_guard else ""
            render.console.print(
                f"  [dim]{who.key} sees: {level.detail} · house rules: {rules}{guard} · "
                f"gravity: {level.gravity_ms}ms[/dim]\n"
            )

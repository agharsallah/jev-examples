"""Command line for the duel."""

from __future__ import annotations

import threading
import webbrowser
from typing import Annotated

import typer

from . import render
from .selfplay import self_play
from .engine import EngineError
from .pilot import BY_KEY, DEFAULT, DIFFICULTIES

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="A self-playing well with Jev at the controls, and one next to it for you.",
)

def _fail(message: str) -> None:
    render.console.print(f"[bold red]The match stopped.[/bold red]\n{message}")
    raise typer.Exit(code=1)


@app.command()
def watch(
    difficulty: Annotated[str, typer.Option("--difficulty", "-d", help=f"One of: {', '.join(BY_KEY)}.")] = DEFAULT,
    pieces: Annotated[int, typer.Option("--pieces", "-n", help="How many pieces to play.")] = 40,
    seed: Annotated[int | None, typer.Option("--seed", help="Fix the piece order.")] = None,
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model to play, e.g. jev-1.13.0.")] = None,
) -> None:
    """Watch Jev play, one request per piece, in the terminal."""
    if difficulty not in BY_KEY:
        _fail(f"No such difficulty: {difficulty}. Pick one of: {', '.join(BY_KEY)}.")

    render.banner()
    tally = None
    try:
        for rows, payload, tally in self_play(difficulty, seed=seed, pieces=pieces, model=model):
            render.console.clear()
            render.banner()
            render.console.print(
                render.well(
                    rows[-16:],
                    title=f"[bold]{tally.score}[/bold] points · {tally.lines} rows · "
                    f"piece {tally.pieces}/{pieces} · {render.clock(tally.seconds)}",
                    subtitle=f"{BY_KEY[difficulty].label} · next: {payload['piece']}",
                )
            )
            render.console.print(render.reading(payload))
    except EngineError as error:
        _fail(str(error))

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


@app.command()
def bench(
    difficulty: Annotated[list[str] | None, typer.Option("--difficulty", "-d", help="Repeatable; defaults to all of them.")] = None,
    pieces: Annotated[int, typer.Option("--pieces", "-n", help="Pieces per match.")] = 40,
    games: Annotated[int, typer.Option("--games", "-g", help="Matches per difficulty.")] = 1,
    seed: Annotated[int, typer.Option("--seed", help="First seed; each match takes the next one.")] = 1,
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model to play, e.g. jev-1.13.0.")] = None,
) -> None:
    """Play the same pieces at every difficulty and print what each one scored.

    One request per piece, so `-n 40 -g 1` over four difficulties is 160 calls.
    Every difficulty gets the same seeds, so the only thing that differs between
    two rows of the table is what Jev was told and what the house rules did.
    """
    keys = difficulty or list(BY_KEY)
    for key in keys:
        if key not in BY_KEY:
            _fail(f"No such difficulty: {key}. Pick from: {', '.join(BY_KEY)}.")

    render.banner()
    results = []
    for key in keys:
        for game in range(games):
            tally = None
            with render.console.status(f"[magenta]{BY_KEY[key].label}[/magenta] match {game + 1}…"):
                try:
                    for move in self_play(key, seed=seed + game, pieces=pieces, model=model):
                        tally = move[2]
                except EngineError as error:
                    _fail(str(error))
            if tally is not None:
                results.append(tally)
                render.console.print(render.scoreline(BY_KEY[key].label, tally, pieces))
    render.console.print(render.bench_table(results, BY_KEY, pieces, games))


@app.command()
def serve(
    port: Annotated[int, typer.Option("--port", "-p", help="Port to sit on.")] = 8000,
    host: Annotated[str, typer.Option("--host", help="Interface to bind.")] = "127.0.0.1",
    open_browser: Annotated[bool, typer.Option("--open/--no-open", help="Open the arcade in a browser.")] = True,
) -> None:
    """Open the arcade: Jev's well on the left, yours on the right."""
    import uvicorn  # A CLI that never serves should not pay for this import.

    from .web import create_app

    url = f"http://{host}:{port}"
    render.banner()
    render.console.print(f"[dim]the arcade is open at[/dim] [bold]{url}[/bold]  [dim](ctrl-c to close)[/dim]\n")
    if open_browser:
        threading.Timer(0.8, webbrowser.open, args=[url]).start()
    uvicorn.run(create_app(), host=host, port=port, log_level="warning")


@app.command()
def levels() -> None:
    """What each difficulty actually changes."""
    render.banner()
    for level in DIFFICULTIES:
        render.console.print(f"[bold magenta]{level.label}[/bold magenta] [dim]({level.key})[/dim]")
        render.console.print(f"  {level.blurb}")
        rules = "on" if level.house_rules else "off"
        guard = " + slot guard" if level.well_guard else ""
        render.console.print(
            f"  [dim]jev sees: {level.detail} · house rules: {rules}{guard} · "
            f"gravity: {level.gravity_ms}ms[/dim]\n"
        )


if __name__ == "__main__":
    app()

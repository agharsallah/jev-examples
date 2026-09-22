"""Command line for the duel."""

from __future__ import annotations

import random
import threading
import webbrowser
from typing import Annotated

import typer

from . import render
from .board import PIECES, empty_grid
from .duel import GameOver, as_payload, next_well, play_piece
from .engine import EngineError
from .pilot import BY_KEY, DEFAULT, DIFFICULTIES

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="A self-playing well with Jev at the controls, and one next to it for you.",
)

LINE_SCORES = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}


def _fail(message: str) -> None:
    render.console.print(f"[bold red]The match stopped.[/bold red]\n{message}")
    raise typer.Exit(code=1)


def _bag(rng: random.Random):
    """The standard seven-bag: every piece once, then shuffle again."""
    while True:
        pieces = list(PIECES)
        rng.shuffle(pieces)
        yield from pieces


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

    rng = random.Random(seed)
    upcoming = _bag(rng)
    rows = list(empty_grid())
    score = lines = 0
    render.banner()

    piece = next(upcoming)
    for count in range(1, pieces + 1):
        following = next(upcoming)
        try:
            decision, menu, level = play_piece(
                rows, piece, following, rows_cleared=lines, level_key=difficulty, model=model
            )
        except GameOver:
            render.console.print("\n[bold red]Topped out.[/bold red] The well is full.")
            break
        except EngineError as error:
            _fail(str(error))

        payload = as_payload(decision, menu, level)
        rows, cleared = next_well(rows, payload["cells"])
        lines += cleared
        score += LINE_SCORES[cleared] * (lines // 10 + 1)

        render.console.clear()
        render.banner()
        render.console.print(
            render.well(
                rows[-16:],
                title=f"[bold]{score}[/bold] points · {lines} rows · piece {count}/{pieces}",
                subtitle=f"{level.label} · next: {following}",
            )
        )
        render.console.print(render.reading(payload))
        piece = following

    render.console.print(
        f"\n[bold magenta]{score}[/bold magenta] points from [bold]{lines}[/bold] rows. "
        f"[dim]Play it yourself with `duel serve`.[/dim]\n"
    )


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
        render.console.print(
            f"  [dim]jev sees: {level.detail} · house rules: "
            f"{'on' if level.house_rules else 'off'} · gravity: {level.gravity_ms}ms[/dim]\n"
        )


if __name__ == "__main__":
    app()

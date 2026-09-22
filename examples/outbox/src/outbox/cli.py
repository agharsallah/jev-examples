"""Command line for the outbox desk."""

from __future__ import annotations

import sys
import threading
import webbrowser
from typing import Annotated

import typer

from . import render
from .audience import AUDIENCES
from .desk import DeskError, models
from .reviewer import Draft, measure_stability, review, review_all
from .samples import SAMPLES

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="A second opinion on anything you are about to send. Jev reads it; your code decides.",
)

AUDIENCE_HELP = f"Who is reading it: {', '.join(AUDIENCES)}. Inferred from --to otherwise."


def _fail(message: str) -> None:
    render.console.print(f"[bold red]The desk could not read it.[/bold red]\n{message}")
    raise typer.Exit(code=1)


def _read_draft(words: list[str]) -> str:
    text = " ".join(words).strip()
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    if not text:
        _fail("Nothing to read. Pass a draft, or pipe one in.")
    return text


@app.command()
def check(
    draft: Annotated[list[str] | None, typer.Argument(help="The message you are about to send.")] = None,
    to: Annotated[str | None, typer.Option("--to", "-t", help="Who it is going to, in your own words.")] = None,
    goal: Annotated[str | None, typer.Option("--goal", "-g", help="What you want to happen once they read it.")] = None,
    channel: Annotated[str | None, typer.Option("--channel", help="email, slack, PR comment, text...")] = None,
    audience: Annotated[str | None, typer.Option("--audience", "-a", help=AUDIENCE_HELP)] = None,
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model to read it, e.g. jev-1.13.0.")] = None,
    deep: Annotated[bool, typer.Option("--deep/--quick", help="Also ask about each sentence (a second request).")] = True,
    runs: Annotated[int, typer.Option("--runs", "-r", min=1, max=12, help="Read it this many times and report how much the verdict moves.")] = 1,
) -> None:
    """Read a draft and say whether to send it."""
    text = _read_draft(draft or [])
    message = Draft(text=text, to=to, goal=goal, channel=channel)

    render.banner()
    try:
        with render.console.status("[dim]reading...[/dim]"):
            result = review(message, audience_key=audience, model=model, deep=deep)
        render.report(result)

        if runs > 1:
            with render.console.status(f"[dim]reading it {runs} more times...[/dim]"):
                stability = measure_stability(
                    message, runs=runs, audience_key=audience, model=model
                )
            render.stability_report(stability)
    except DeskError as error:
        _fail(str(error))


@app.command()
def demo(
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model to read them.")] = None,
    full: Annotated[bool, typer.Option("--full", help="Print the whole report for each draft.")] = False,
) -> None:
    """Run the bundled drafts past the desk, all at once."""
    render.banner()
    try:
        with render.console.status(f"[dim]reading {len(SAMPLES)} drafts...[/dim]"):
            reviews = review_all(SAMPLES, model=model)
    except DeskError as error:
        _fail(str(error))

    if full:
        for result in reviews:
            render.report(result)
    else:
        render.batch_report(reviews)


@app.command()
def serve(
    port: Annotated[int, typer.Option("--port", "-p", help="Port to sit on.")] = 8000,
    host: Annotated[str, typer.Option("--host", help="Interface to bind.")] = "127.0.0.1",
    open_browser: Annotated[bool, typer.Option("--open/--no-open", help="Open the desk in a browser.")] = True,
) -> None:
    """Open the desk in a browser: the same review, with the draft marked up."""
    import uvicorn  # A CLI that never serves should not pay for this import.

    from .web import create_app

    url = f"http://{host}:{port}"
    render.banner()
    render.console.print(f"[dim]the desk is open at[/dim] [bold]{url}[/bold]  [dim](ctrl-c to close)[/dim]\n")
    if open_browser:
        threading.Timer(0.8, webbrowser.open, args=[url]).start()
    uvicorn.run(create_app(), host=host, port=port, log_level="warning")


@app.command(name="models")
def models_command() -> None:
    """Which models this key can send a draft to."""
    try:
        render.models_report(models())
    except DeskError as error:
        _fail(str(error))


if __name__ == "__main__":
    app()

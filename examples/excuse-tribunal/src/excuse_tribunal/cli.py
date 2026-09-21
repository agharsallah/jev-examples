"""Command line for the Excuse Tribunal."""

from __future__ import annotations

import subprocess
import sys
import threading
import webbrowser
from typing import Annotated

import typer

from . import rap_sheet, render
from .questions import commit_docket, excuse_docket
from .tribunal import TribunalError, hear_case
from .verdict import deliberate

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="A courtroom for your excuses. Jev presides; your code passes sentence.",
)


def _fail(message: str) -> None:
    render.console.print(f"[bold red]The hearing collapsed.[/bold red]\n{message}")
    raise typer.Exit(code=1)


def _read_excuse(excuse: list[str]) -> str:
    text = " ".join(excuse).strip()
    if text:
        return text
    if not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    if not text:
        _fail("Nothing was said in your defence. Pass an excuse, or pipe one in.")
    return text


@app.command()
def judge(
    excuse: Annotated[list[str] | None, typer.Argument(help="What you would like the court to believe.")] = None,
    context: Annotated[str | None, typer.Option("--context", "-c", help="What you were actually supposed to do.")] = None,
    audience: Annotated[str | None, typer.Option("--audience", "-a", help="Who you are telling this to.")] = None,
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model to try the case, e.g. jev-1.13.0.")] = None,
    keep: Annotated[bool, typer.Option("--keep/--no-keep", help="Add the hearing to your rap sheet.")] = True,
) -> None:
    """Put an excuse on trial."""
    text = _read_excuse(excuse or [])

    # A structured state gives Jev the surrounding facts without pretending
    # they are part of the excuse itself.
    state = {"excuse": text}
    if context:
        state["what_was_expected"] = context
    if audience:
        state["told_to"] = audience

    render.banner()
    try:
        with render.console.status("[dim]the court is deliberating...[/dim]"):
            response = hear_case(state, excuse_docket(), model=model)
    except TribunalError as error:
        _fail(str(error))

    verdict = deliberate(response.answers)
    render.verdict_report(text, verdict)
    if keep:
        rap_sheet.record("excuse", text, verdict)


@app.command()
def commit(
    rev: Annotated[str, typer.Option("--rev", "-r", help="Which commit to try.")] = "HEAD",
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model to try the case.")] = None,
    keep: Annotated[bool, typer.Option("--keep/--no-keep", help="Add the hearing to your rap sheet.")] = True,
) -> None:
    """Put a git commit message on trial for what it claims about the change."""
    try:
        message = subprocess.run(
            ["git", "log", "-1", "--pretty=%B", rev],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        files = subprocess.run(
            ["git", "show", "--name-only", "--pretty=format:", rev],
            capture_output=True, text=True, check=True,
        ).stdout.split()
    except FileNotFoundError:
        _fail("git is not installed, so there is nothing to try.")
    except subprocess.CalledProcessError as error:
        _fail(f"git could not find {rev}: {error.stderr.strip()}")

    if not message:
        _fail(f"{rev} has an empty commit message. That is its own kind of guilt.")

    # The files are the evidence: they let Jev judge the message against what
    # the commit actually touched, not just against itself.
    state = {"commit_message": message, "files_changed": files[:50]}

    render.banner()
    try:
        with render.console.status("[dim]the court is reading the diff...[/dim]"):
            response = hear_case(state, commit_docket(), model=model)
    except TribunalError as error:
        _fail(str(error))

    verdict = deliberate(response.answers)
    render.verdict_report(message, verdict)
    if keep:
        rap_sheet.record("commit", message, verdict)


@app.command()
def serve(
    port: Annotated[int, typer.Option("--port", "-p", help="Port to sit on.")] = 8000,
    host: Annotated[str, typer.Option("--host", help="Interface to bind.")] = "127.0.0.1",
    open_browser: Annotated[bool, typer.Option("--open/--no-open", help="Open the courtroom in a browser.")] = True,
) -> None:
    """Hold court in a browser: the same hearing, with better theatre."""
    import uvicorn  # A CLI that never serves should not pay for this import.

    from .web import create_app

    url = f"http://{host}:{port}"
    render.banner()
    render.console.print(f"[dim]the court is in session at[/dim] [bold]{url}[/bold]  [dim](ctrl-c to adjourn)[/dim]\n")
    if open_browser:
        threading.Timer(0.8, webbrowser.open, args=[url]).start()
    uvicorn.run(create_app(), host=host, port=port, log_level="warning")


@app.command(name="rap-sheet")
def rap_sheet_command() -> None:
    """Show everything the court has on you."""
    records = rap_sheet.history()
    render.rap_sheet_report(records, rap_sheet.summary(records))


@app.command()
def expunge(
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation.")] = False,
) -> None:
    """Destroy your record. The court does not endorse this."""
    if not rap_sheet.RAP_SHEET.exists():
        render.console.print("[dim]Nothing to expunge.[/dim]")
        return
    if not yes:
        typer.confirm(f"Delete {rap_sheet.RAP_SHEET}?", abort=True)
    rap_sheet.RAP_SHEET.unlink()
    render.console.print("[dim]Record sealed. As far as anyone knows, you were never here.[/dim]")


if __name__ == "__main__":
    app()

"""Command line for triage."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Annotated

import typer

from . import github, render
from .evaluate import evaluate
from .jev import TriageError
from .overview import overview
from .scan import scan
from .triage import read_repo, triage

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Point it at any GitHub repo. Jev reads the labels, then the issues; your code decides. Read-only.",
)

Model = Annotated[
    str | None, typer.Option("--model", "-m", help="Model to read with, e.g. jev-1.13.0.")
]


def _fail(message: str) -> None:
    render.console.print(f"[bold red]Triage stopped.[/bold red]\n{message}")
    raise typer.Exit(code=1)


@app.command()
def taxonomy(
    repo: Annotated[str, typer.Argument(help="owner/repo or a github.com URL.")],
    model: Model = None,
    refresh: Annotated[
        bool, typer.Option("--refresh", help="Re-fetch labels from GitHub.")
    ] = False,
) -> None:
    """How Jev reads a repo's labels, and the questions that fall out of it."""
    render.banner()
    try:
        with render.console.status("[dim]reading the labels...[/dim]"):
            _, tax = read_repo(repo, model=model, refresh=refresh)
    except TriageError as error:
        _fail(str(error))
    render.taxonomy_report(tax)


@app.command()
def issue(
    ref: Annotated[str, typer.Argument(help="owner/repo#123, or an issue URL.")],
    model: Model = None,
    fresh: Annotated[
        bool, typer.Option("--fresh", help="Re-read the issue from GitHub and ask Jev again.")
    ] = False,
    search: Annotated[
        bool, typer.Option("--search/--no-search", help="Search the repo's history for duplicates.")
    ] = True,
    as_json: Annotated[
        bool, typer.Option("--json", help="Print the measurement and verdict as JSON.")
    ] = False,
    raw: Annotated[
        bool, typer.Option("--raw", help="Print the exact request sent to Jev as JSON.")
    ] = False,
    trace: Annotated[
        bool, typer.Option("--trace/--no-trace", help="Show the policy trace.")
    ] = True,
) -> None:
    """Triage one issue: one request, every question, and the working."""
    try:
        _, _, number = github.parse(ref)
        if number is None:
            _fail("Which issue? Pass owner/repo#123.")
        if not (as_json or raw):
            render.banner()
        with render.console.status("[dim]reading the issue...[/dim]"):
            m, assessment, request = triage(ref, model=model, fresh=fresh, search=search)
    except TriageError as error:
        _fail(str(error))
    if raw:
        print(json.dumps(request, indent=2))
    elif as_json:
        print(json.dumps({"measurement": m, "assessment": asdict(assessment)}, indent=2))
    else:
        render.issue_report(m, assessment, trace=trace)


@app.command(name="scan")
def scan_command(
    repo: Annotated[str, typer.Argument(help="owner/repo or a github.com URL.")],
    limit: Annotated[
        int, typer.Option("--limit", "-n", min=1, max=500, help="How many recent open issues.")
    ] = 100,
    model: Model = None,
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Re-fetch from GitHub instead of using what is on disk."),
    ] = False,
) -> None:
    """Triage the most recent open issues, all at once, and sort them into lanes."""
    render.banner()
    try:
        with render.console.status(
            f"[dim]reading {limit} issues, {8} at a time...[/dim]"
        ) as status:
            result = scan(
                repo,
                refresh=refresh,
                limit=limit,
                model=model,
                on_progress=lambda done, total: status.update(f"[dim]read {done}/{total}...[/dim]"),
            )
    except TriageError as error:
        _fail(str(error))
    render.scan_report(result)


@app.command(name="overview")
def overview_command(
    repo: Annotated[str, typer.Argument(help="owner/repo or a github.com URL.")],
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            "-n",
            min=1,
            max=1000,
            help="Read only the newest N open issues (default: all).",
        ),
    ] = None,
    model: Model = None,
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Re-fetch from GitHub instead of using what is on disk."),
    ] = False,
    as_json: Annotated[
        bool, typer.Option("--json", help="Print the whole overview as JSON.")
    ] = False,
) -> None:
    """Every open issue at once: what's ready, what a newcomer could take, what's a duplicate."""
    if not as_json:
        render.banner()
    try:
        with render.console.status("[dim]fetching the open issues...[/dim]") as status:
            result = overview(
                repo,
                refresh=refresh,
                limit=limit,
                model=model,
                on_progress=lambda done, total: status.update(f"[dim]read {done}/{total}...[/dim]"),
            )
    except TriageError as error:
        _fail(str(error))
    if as_json:
        print(json.dumps(result, indent=2))
    else:
        render.overview_report(result)


@app.command(name="eval")
def eval_command(
    repo: Annotated[str, typer.Argument(help="owner/repo or a github.com URL.")],
    limit: Annotated[
        int,
        typer.Option(
            "--limit", "-n", min=10, max=500, help="How many labelled issues to score against."
        ),
    ] = 150,
    model: Model = None,
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Re-fetch from GitHub instead of using what is on disk."),
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print the report as JSON.")] = False,
) -> None:
    """Score agreement with the labels people already put on issues, and calibration."""
    if not as_json:
        render.banner()
    try:
        with render.console.status(f"[dim]reading {limit} labelled issues...[/dim]") as status:
            report = evaluate(
                repo,
                refresh=refresh,
                limit=limit,
                model=model,
                on_progress=lambda done, total: status.update(f"[dim]read {done}/{total}...[/dim]"),
            )
    except TriageError as error:
        _fail(str(error))
    report.pop("measurements", None)
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        render.eval_report(report)


@app.command()
def serve(
    port: Annotated[int, typer.Option("--port", "-p", help="Port to sit on.")] = 8000,
    host: Annotated[str, typer.Option("--host", help="Interface to bind.")] = "127.0.0.1",
    open_browser: Annotated[
        bool, typer.Option("--open/--no-open", help="Open it in a browser.")
    ] = True,
) -> None:
    """Open the triage desk in a browser."""
    import threading
    import webbrowser

    import uvicorn  # A CLI that never serves should not pay for this import.

    from .web import create_app

    url = f"http://{host}:{port}"
    render.banner()
    render.console.print(f"[dim]open at[/dim] [bold]{url}[/bold]  [dim](ctrl-c to close)[/dim]\n")
    if open_browser:
        threading.Timer(0.8, webbrowser.open, args=[url]).start()
    uvicorn.run(create_app(), host=host, port=port, log_level="warning")


if __name__ == "__main__":
    app()

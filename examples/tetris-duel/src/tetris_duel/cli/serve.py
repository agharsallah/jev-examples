"""The arcade: one app for every installed player, matchup picked on the page."""

from __future__ import annotations

import threading
import webbrowser
from typing import Annotated

import typer

from .. import render


def serve(
    port: Annotated[int, typer.Option("--port", "-p", help="Port to sit on.")] = 8000,
    host: Annotated[str, typer.Option("--host", help="Interface to bind.")] = "127.0.0.1",
    open_browser: Annotated[bool, typer.Option("--open/--no-open", help="Open the arcade in a browser.")] = True,
    left: Annotated[str, typer.Option("--left", help="Who starts in the left-hand well, e.g. jev or laya.")] = "jev",
    right: Annotated[str, typer.Option("--right", help="Who starts in the right-hand well: you, or a model.")] = "you",
) -> None:
    """Open the arcade. Pick who plays which well on the page; these only set the start."""
    import uvicorn  # A CLI that never serves should not pay for this import.

    from ..players import installed
    from ..web import create_app

    players = installed()
    url = f"http://{host}:{port}"
    render.banner()
    for player in players.values():
        blocked = player.blocked()
        note = f"[yellow]{blocked}[/yellow]" if blocked else "[green]ready[/green]"
        render.console.print(f"  [bold]{player.name}[/bold] [dim]({player.key})[/dim]  {note}")
    render.console.print(f"\n[dim]the arcade is open at[/dim] [bold]{url}[/bold]  [dim](ctrl-c to close)[/dim]\n")
    if open_browser:
        start = f"{url}/?left={left}&right={right}"
        threading.Timer(0.8, webbrowser.open, args=[start]).start()
    uvicorn.run(create_app(players), host=host, port=port, log_level="warning")

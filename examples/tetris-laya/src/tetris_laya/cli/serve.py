"""The arcade, opened on a Laya matchup."""

from __future__ import annotations

import threading
import webbrowser
from typing import Annotated

import typer
from tetris_duel import render

from .common import MODEL_HELP, TAGLINE, load_model, need_jev


def serve(
    port: Annotated[int, typer.Option("--port", "-p", help="Port to sit on.")] = 8001,
    host: Annotated[str, typer.Option("--host", help="Interface to bind.")] = "127.0.0.1",
    open_browser: Annotated[
        bool, typer.Option("--open/--no-open", help="Open the arcade in a browser.")
    ] = True,
    model: Annotated[str | None, typer.Option("--model", "-m", help=MODEL_HELP)] = None,
    versus: Annotated[
        bool, typer.Option("--versus", help="Put Jev in the right-hand well instead of you.")
    ] = False,
) -> None:
    """Open the arcade with Laya on the left, you (or Jev) on the right.

    It is the one `duel serve` app, with this matchup picked for you; the page can
    switch to any other.
    """
    import os

    import uvicorn
    from tetris_duel.web import create_app

    from .engine import MODEL_ENV

    if model:
        os.environ[MODEL_ENV] = model
    if versus:
        need_jev()
    render.banner("Laya", TAGLINE)
    load_model(model)
    url = f"http://{host}:{port}/?left=laya&right={'jev' if versus else 'you'}"
    render.console.print(
        f"[dim]the arcade is open at[/dim] [bold]{url}[/bold]  [dim](ctrl-c to close)[/dim]\n"
    )
    if open_browser:
        threading.Timer(0.8, webbrowser.open, args=[url]).start()
    uvicorn.run(create_app(), host=host, port=port, log_level="warning")

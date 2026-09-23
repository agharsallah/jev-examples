"""Command line for the duel. One module per group of commands; this file only puts them on the app.

Every command takes any installed player (see `players.py`), so a package that
registers one -- tetris-laya does -- gets watch, bench, versus and the arcade
without a command line of its own.
"""

from __future__ import annotations

import typer

from .serve import serve
from .solo import bench, levels, watch
from .versus import versus

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="A self-playing well: Jev, or any installed player, at the controls, and one next to it for you.",
)

for command in (watch, bench, versus, serve, levels):
    app.command()(command)

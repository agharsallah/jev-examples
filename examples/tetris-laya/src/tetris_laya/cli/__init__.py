"""Command line for the Laya duel: the Jev harness's commands, with Laya playing.

One module per group of commands; this file only puts them on the app.
"""

from __future__ import annotations

import typer

from .serve import serve
from .solo import bench, levels, watch
from .versus import versus

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="A self-playing well with a local Laya model at the controls, and one next to it for you.",
)


for command in (watch, bench, serve, versus, levels):
    app.command()(command)

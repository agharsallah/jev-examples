"""What every Laya command shares: failing politely, loading the model, the key check."""

from __future__ import annotations

import os

import typer
from tetris_duel import render
from tetris_duel.engine import API_KEY_ENV, MISSING_KEY, EngineError, load_env

from ..engine import DEFAULT_MODEL, model_id
from ..levels import BY_KEY

TAGLINE = "a self-playing well · one local forward pass per round"


def fail(message: str) -> None:
    render.console.print(f"[bold red]The match stopped.[/bold red]\n{message}")
    raise typer.Exit(code=1)


def check(keys: list[str]) -> None:
    for key in keys:
        if key not in BY_KEY:
            fail(f"No such difficulty: {key}. Pick one of: {', '.join(BY_KEY)}.")


def load_model(model: str | None) -> None:
    """Load the checkpoint up front, so the first piece is not a mystery pause."""
    from .engine import agent

    with render.console.status(
        f"[magenta]loading {model_id(model)}[/magenta] (first run downloads ~1.3 GB)…"
    ):
        try:
            agent(model)
        except EngineError as error:
            fail(str(error))


MODEL_HELP = f"Hugging Face repo or local path of a Laya checkpoint. Default: {DEFAULT_MODEL}, or $LAYA_MODEL."


def need_jev() -> None:
    """Jev is the one player here that needs a key; say so before the match, not during it."""
    load_env()
    if not os.environ.get(API_KEY_ENV, "").strip():
        fail(MISSING_KEY.replace("nobody is playing the left-hand board", "Jev cannot play"))

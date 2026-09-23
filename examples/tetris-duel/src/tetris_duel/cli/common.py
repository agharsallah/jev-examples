"""What every command shares: failing politely, and getting a player to the table."""

from __future__ import annotations

import typer

from .. import render
from ..engine import EngineError
from ..pilot import Difficulty
from ..players import Player, installed

DEFAULT_LEVEL = "grandmaster"
PLAYER_HELP = "Who plays: jev, or any installed player such as laya."
MODEL_HELP = "Model for the player: a Jev model name, or a Laya checkpoint (repo id or path)."


def fail(message: str) -> None:
    render.console.print(f"[bold red]The match stopped.[/bold red]\n{message}")
    raise typer.Exit(code=1)


def levels_of(player: Player) -> dict[str, Difficulty]:
    return {level.key: level for level in player.levels}


def check_levels(player: Player, keys: list[str]) -> None:
    ladder = levels_of(player)
    for key in keys:
        if key not in ladder:
            fail(f"No such difficulty: {key}. Pick one of: {', '.join(ladder)}.")


def seat(key: str, model: str | None = None) -> Player:
    """An installed player that can play right now, warmed up so the first piece is not a stall.

    Warming loads the player's default model, so a match on another one skips it
    and pays for the load on its first piece instead.
    """
    players = installed()
    if key not in players:
        fail(f"No such player: {key}. Installed: {', '.join(players)}.")
    player = players[key]
    blocked = player.blocked()
    if blocked:
        fail(f"{player.name} cannot play: it {blocked}.")
    if player.warm and model is None:
        with render.console.status(f"[magenta]getting {player.name} ready[/magenta]…"):
            try:
                player.warm()
            except EngineError as error:
                fail(str(error))
    return player

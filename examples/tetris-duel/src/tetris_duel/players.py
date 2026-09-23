"""Who can sit at a well.

Jev is built in. Any other package can add a player by exposing a function
that returns a `Player` under the `tetris_duel.players` entry point group --
`tetris-laya` does, for a model that runs locally -- and the arcade offers
whatever is installed. Nothing here imports a player's engine until it plays.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import entry_points

from .pilot import DIFFICULTIES, Difficulty

ENTRY_POINTS = "tetris_duel.players"


@dataclass(frozen=True)
class Player:
    key: str
    name: str
    play: Callable  # same signature as duel.play_piece
    levels: tuple[Difficulty, ...]
    about: str  # one paragraph, may hold links, shown under the match
    blocked: Callable[[], str | None] = lambda: None  # why it cannot play right now
    warm: Callable[[], None] | None = None  # load whatever is slow, before the first piece


def _jev_blocked() -> str | None:
    from .engine import API_KEY_ENV, load_env

    load_env()
    if not os.environ.get(API_KEY_ENV, "").strip():
        return f"needs {API_KEY_ENV}"
    return None


def _jev_plays(*args, **kwargs):
    from .jev import play_piece

    return play_piece(*args, **kwargs)


JEV = Player(
    key="jev",
    name="Jev",
    play=_jev_plays,
    levels=DIFFICULTIES,
    about=(
        'Jev plays over the <a href="https://docs.typesafe.ai/models">TypeSafe API</a>: one '
        "request per piece, carrying a "
        '<a href="https://docs.typesafe.ai/primitives/choice">Choice</a> over every legal landing, '
        'a <a href="https://docs.typesafe.ai/primitives/score">Score</a> for how much trouble the '
        'well is in, a <a href="https://docs.typesafe.ai/primitives/noul">Noul</a> on whether to '
        "clear rows now and, on Grandmaster, one more on whether a named column is worth keeping "
        "empty. Everything it is told is worked out in code and handed over in words, and "
        "difficulty is how much of that it gets."
    ),
    blocked=_jev_blocked,
)


def installed() -> dict[str, Player]:
    """Jev, plus every player another installed package has registered."""
    players = {JEV.key: JEV}
    for entry in entry_points(group=ENTRY_POINTS):
        try:
            player = entry.load()()
        except Exception:  # a broken plugin should cost its own seat, not the arcade
            continue
        players.setdefault(player.key, player)
    return players

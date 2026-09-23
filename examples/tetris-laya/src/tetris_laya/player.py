"""Laya's seat in the tetris duel arcade.

Registered under the `tetris_duel.players` entry point, so `duel serve` offers
Laya whenever this package is installed. torch is only imported once Laya is
asked to play or to warm up.
"""

from __future__ import annotations

from tetris_duel.players import Player

from .levels import LEVELS

ABOUT = (
    '<a href="https://huggingface.co/convaiinnovations/laya-multilingual">Laya</a> plays on '
    "this machine: a 322M-parameter decision model, no key, no network after the first "
    "download. It gives each question 256 tokens for its options and a well can offer 34 "
    "landings, so the menu runs as heats that fit, the winners meet in a final, and the "
    "probabilities are multiplied back down so every landing keeps its share. The danger "
    "rubric and the yes-or-no questions are asked as plain choices, as the model card advises."
)


def _plays(*args, **kwargs):
    from .play import play_piece

    return play_piece(*args, **kwargs)


def _warm() -> None:
    from .engine import agent

    agent()


def player() -> Player:
    return Player(key="laya", name="Laya", play=_plays, levels=LEVELS, about=ABOUT, warm=_warm)

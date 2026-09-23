"""How Jev is asked about one piece: the whole docket, in one request.

This is Jev's `Asker` for `duel.play`. Everything else about a move -- the
menu, the slot, the house rules -- is the shared harness.
"""

from __future__ import annotations

from functools import partial

from .duel import Reply, Turn, play
from .engine import ask
from .pilot import Difficulty, difficulty
from .questions import describe, move_docket, slot_question, well_state


class Jev:
    name = "Jev"

    def difficulty(self, key: str | None) -> Difficulty:
        return difficulty(key)

    def ask(self, turn: Turn) -> Reply:
        detail = turn.level.detail
        shown = {
            spot: describe(landing, detail, turn.next_piece) for spot, landing in turn.menu.items()
        }
        slot = None if turn.slot is None else slot_question(turn.grid, turn.slot, turn.since_bar)
        response = ask(
            well_state(turn.grid, turn.piece, turn.next_piece, turn.rows_cleared, detail),
            move_docket(shown, slot),
            model=turn.model,
        )
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return Reply(response.answers, response.model, usage)


JEV = Jev()

# The shared harness with Jev asking: what the arcade, self-play and bench call.
play_piece = partial(play, JEV)

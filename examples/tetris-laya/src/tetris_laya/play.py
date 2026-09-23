"""How Laya is asked about one piece: heats, a final, and the side questions.

This is Laya's `Asker` for `tetris_duel.duel.play`. The menu, the slot, the
house rules and the timing are the shared harness, exactly as they are for
Jev; only the asking below is Laya's own.
"""

from __future__ import annotations

from functools import partial
from types import SimpleNamespace

import numpy as np
from laya import confidence_from_probs
from tetris_duel.duel import Reply, Turn, play
from tetris_duel.engine import EngineError
from tetris_duel.pilot import Difficulty
from tetris_duel.questions import DANGER_LEVELS

from .engine import ask, count_tokens, head_budget, model_id
from .levels import difficulty
from .phrasing import describe, well_state
from .questions import DANGER_KEYS, YES, heat, heats, side_questions


class Laya:
    name = "Laya"

    def difficulty(self, key: str | None) -> Difficulty:
        return difficulty(key)

    def ask(self, turn: Turn) -> Reply:
        detail = turn.level.detail
        texts = {
            spot: describe(landing, detail, turn.next_piece) for spot, landing in turn.menu.items()
        }
        state = well_state(turn.grid, turn.piece, turn.next_piece, turn.rows_cleared, detail)
        side = side_questions(turn.grid, turn.slot, turn.since_bar)
        probabilities, side_answers, usage = tournament(state, texts, side, turn.model)
        return Reply(answers(probabilities, side_answers), model_id(turn.model), usage)


LAYA = Laya()

# The shared harness with Laya asking: what the arcade and self-play call.
play_piece = partial(play, LAYA)


def tournament(
    state: dict,
    texts: dict[str, str],
    side: dict,
    model: str | None = None,
) -> tuple[dict[str, float], dict, dict]:
    """Heats, then winners' heats, until one question holds the whole field.

    Each round is one forward pass, with every heat of that round in it; the
    side questions ride along with the first. A landing's final probability is
    its share of its own heat times the probability of that heat's winner in
    the round above, all the way to the top, so the numbers still sum to one
    and a landing that lost a close heat keeps a close second's weight.
    """
    budget = head_budget(model)
    count = lambda text: count_tokens(text, model)  # noqa: E731
    field = list(texts)
    rounds: list[list[tuple[list[str], dict[str, float]]]] = []
    side_answers: dict = {}
    usage = {"input_tokens": 0, "output_tokens": 0, "passes": 0}

    while True:
        groups = heats(field, texts, budget, count)
        if len(groups) == len(field) > 1:
            groups = [field[i : i + 2] for i in range(0, len(field), 2)]  # never stall
        asked = {f"heat_{i}": heat(g, texts) for i, g in enumerate(groups) if len(g) > 1}
        if not rounds:
            asked.update(side)
        if asked:
            response = ask(state, asked, model)
            usage["input_tokens"] += response["usage"]["input_tokens"]
            usage["passes"] += 1
            got = response["answers"]
        else:
            got = {}
        if not rounds:
            side_answers = {key: got[key] for key in side}

        results = []
        for i, group in enumerate(groups):
            if len(group) == 1:
                results.append((group, {group[0]: 1.0}))
            else:
                results.append((group, got[f"heat_{i}"]["probabilities"]))
        rounds.append(results)
        if len(groups) == 1:
            break
        field = [max(group, key=probs.get) for group, probs in results]

    # Top down: the final gives each finalist its weight, and every heat below
    # shares its winner's weight among its runners in its own proportions.
    weight = {spot: 1.0 for spot in rounds[-1][0][0]}
    for results in reversed(rounds):
        below = {}
        for group, probs in results:
            winner = max(group, key=probs.get)
            for spot in group:
                below[spot] = probs[spot] * weight[winner]
        weight = below
    return weight, side_answers, usage


def answers(probabilities: dict[str, float], side: dict) -> dict:
    """Laya's answers, read back into the shape `pilot.decide` takes from Jev."""
    try:
        picked = max(probabilities, key=probabilities.get)
        values = np.array(list(probabilities.values()))
        danger = side["danger"]["probabilities"]
        out = {
            "landing": SimpleNamespace(
                choice=picked,
                probabilities=probabilities,
                confidence=confidence_from_probs(values, len(values)),
            ),
            "danger": SimpleNamespace(
                score=sum(i * danger[key] for i, key in enumerate(DANGER_KEYS)),
                legend=dict(enumerate(DANGER_LEVELS)),
            ),
            "clear_now": SimpleNamespace(noul=side["clear_now"]["probabilities"][YES]),
            "mood": SimpleNamespace(choice=side["mood"]["choice"]),
        }
        if "keep_the_slot" in side:
            out["keep_the_slot"] = SimpleNamespace(noul=side["keep_the_slot"]["probabilities"][YES])
    except KeyError as error:
        raise EngineError(f"Laya's answer was missing {error}") from error
    return out

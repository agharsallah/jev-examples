"""One falling piece, with Laya choosing where it goes.

A drop-in for `tetris_duel.duel.play_piece`: same arguments, same return value,
so the arcade, the terminal and the bench all run unchanged. The board, the
legal landings and the house rules are the Jev harness's own; only the asking
is different.
"""

from __future__ import annotations

import time
from types import SimpleNamespace

import numpy as np
from laya import confidence_from_probs
from tetris_duel.board import Landing, landings, read_grid, slot_column
from tetris_duel.duel import GameOver
from tetris_duel.engine import EngineError
from tetris_duel.pilot import Decision, Difficulty, decide
from tetris_duel.questions import DANGER_LEVELS

from .engine import ask, count_tokens, head_budget, model_id
from .levels import difficulty
from .phrasing import describe, well_state
from .questions import DANGER_KEYS, YES, heat, heats, side_questions


def play_piece(
    rows: list[str],
    piece: str,
    next_piece: str | None = None,
    rows_cleared: int = 0,
    level_key: str | None = None,
    model: str | None = None,
    since_bar: int | None = None,
) -> tuple[Decision, dict[str, Landing], Difficulty]:
    """Ask Laya where this piece goes, and let the house rules have the last word."""
    level = difficulty(level_key)
    grid = read_grid(rows)
    options = landings(grid, piece)
    if not options:
        raise GameOver(f"the {piece} piece has nowhere to land")
    by_spot = {f"spot_{i + 1}": landing for i, landing in enumerate(options)}
    texts = {spot: describe(landing, level.detail, next_piece) for spot, landing in by_spot.items()}

    slot = slot_column(grid) if level.well_guard else None
    state = well_state(grid, piece, next_piece, rows_cleared, level.detail)
    started = time.perf_counter()
    probabilities, side, usage = tournament(
        state, texts, side_questions(grid, slot, since_bar), model
    )
    usage["ms"] = round((time.perf_counter() - started) * 1000)

    decision = decide(
        by_spot,
        answers(probabilities, side),
        level,
        model=model_id(model),
        usage=usage,
        slot=slot,
    )
    # The house rules explain themselves in Jev's name; this well has another player.
    decision.note = decision.note.replace("Jev", "Laya")
    return decision, by_spot, level


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

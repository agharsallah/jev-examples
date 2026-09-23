"""A move, in the shape the scoreboard draws it: the arcade's JSON and the terminal's panel."""

from __future__ import annotations

import random

from .board import Landing
from .pilot import Decision, Difficulty

# Jev picks the mood; the phrasing is ours. Selecting a line beats generating
# one -- it keeps the commentary in the same typed world as everything else.
CHEERS = {
    "cruising": ["All calm down here!", "Nice and tidy.", "Easy money.", "Barely breaking a sweat."],
    "tidying_up": ["Smoothing out that step.", "Just a spot of housekeeping.", "Filling in the dent."],
    "digging_out": ["Digging back down to those gaps!", "Spade work.", "Excavation underway."],
    "stacking_dangerously": ["Ooh, that is getting tall...", "Careful now!", "Running out of room!"],
    "setting_up_a_big_clear": ["Something big is brewing!", "Holding out for the long bar.", "Loading up!"],
    "improvising": ["No good options — making the best of it.", "Every choice costs something here.", "Improvising!"],
}



def cheer(mood: str, rng: random.Random | None = None) -> str:
    lines = CHEERS.get(mood, CHEERS["cruising"])
    return (rng or random).choice(lines)


def as_payload(
    decision: Decision,
    menu: dict[str, Landing],
    level: Difficulty,
    shown: int = 6,
) -> dict:
    """Everything the scoreboard draws, in the shape it draws it."""
    ranked = sorted(
        menu.items(),
        key=lambda item: decision.probabilities.get(item[0], 0.0),
        reverse=True,
    )
    options = [
        {
            "spot": spot,
            "where": landing.where(),
            "probability": decision.probabilities.get(spot, 0.0),
            "rows_cleared": landing.rows_cleared,
            "new_gaps": landing.new_gaps,
            "chosen": spot == decision.spot,
            "jev": spot == decision.picked_by_jev,
        }
        for spot, landing in ranked[:shown]
    ]
    if not any(option["chosen"] for option in options):  # an overruled underdog
        landing = menu[decision.spot]
        options.append(
            {
                "spot": decision.spot,
                "where": landing.where(),
                "probability": decision.probabilities.get(decision.spot, 0.0),
                "rows_cleared": landing.rows_cleared,
                "new_gaps": landing.new_gaps,
                "chosen": True,
                "jev": False,
            }
        )

    landing = decision.landing
    return {
        "piece": landing.piece,
        "rotation": landing.rotation,
        "cells": [[x, y] for x, y in landing.cells],
        "where": landing.where(),
        "rows_cleared": landing.rows_cleared,
        "new_gaps": landing.new_gaps,
        "menu_size": len(menu),
        "options": options,
        "confidence": decision.confidence,
        "torn": decision.torn,
        "sure": decision.sure,
        "column": min(x for x, _ in landing.cells),
        "landing_row": min(y for _, y in landing.cells),
        "danger": {"value": decision.danger, "level": decision.danger_level},
        "clear_now": decision.clear_now,
        "mood": {"key": decision.mood, "line": cheer(decision.mood)},
        "overruled": decision.overruled,
        "note": decision.note,
        "guarding": None if decision.guarding is None else decision.guarding + 1,
        "keep_slot": decision.keep_slot,
        "difficulty": {"key": level.key, "label": level.label, "gravity_ms": level.gravity_ms},
        "model": decision.model,
        "usage": decision.usage,
    }


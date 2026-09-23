"""Laya's difficulty ladder.

Same keys and the same gravity as Jev's, so a seed plays the same game on both
and the arcade can put them side by side; what changes is how much of each
landing fits in a few tokens.
"""

from __future__ import annotations

from tetris_duel.pilot import Difficulty

LEVELS: tuple[Difficulty, ...] = (
    Difficulty(
        key="chill",
        label="Chill",
        detail="position",
        house_rules=False,
        well_guard=False,
        gravity_ms=850,
        blurb="Laya sees the well and where each piece would land. Nothing else: it plays "
        "on shape alone.",
    ),
    Difficulty(
        key="steady",
        label="Steady",
        detail="board",
        house_rules=False,
        well_guard=False,
        gravity_ms=560,
        blurb="Every option also says how tall and how even the stack would be afterwards. "
        "A picture of the well would not fit in Laya's budget; a few words do.",
    ),
    Difficulty(
        key="ruthless",
        label="Ruthless",
        detail="fit",
        house_rules=True,
        well_guard=False,
        gravity_ms=340,
        blurb="Code reads the ground and says what it found, and every option says whether "
        "the piece sits flush or seals cells. When Laya calls the well dangerous, the house "
        "rules re-rank its own probabilities.",
    ),
    Difficulty(
        key="grandmaster",
        label="Grandmaster",
        detail="insight",
        house_rules=True,
        well_guard=True,
        gravity_ms=280,
        blurb="Two plies: every option also says what the next piece could do afterwards, and "
        "the rows closest to completing are named. While Laya says to keep a slot open, the "
        "house rules defend it for a four-row clear.",
    ),
)

BY_KEY = {level.key: level for level in LEVELS}
DEFAULT = "grandmaster"


def difficulty(key: str | None) -> Difficulty:
    return BY_KEY.get((key or DEFAULT).lower(), BY_KEY[DEFAULT])

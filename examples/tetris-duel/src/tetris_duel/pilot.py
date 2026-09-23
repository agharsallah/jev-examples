"""Difficulty, and what the code does with Jev's answers.

Two dials, and neither of them is a hand-written tetris bot. The first is how
much of each landing Jev is allowed to see. The second is whether the house
rules below are allowed to overrule it when the well is in trouble. Everything
here is ordinary Python over typed answers: no network, no hidden heuristic
picking the move behind Jev's back.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .board import Landing

# ------------------------------------------------------------------ difficulty


@dataclass(frozen=True)
class Difficulty:
    key: str
    label: str
    detail: str  # what Jev is shown: position | board | fit | insight
    house_rules: bool  # may the policy below overrule the pick?
    well_guard: bool  # may it defend an open slot for a four-row clear?
    gravity_ms: int  # drop speed, for both boards, so the race is fair
    blurb: str


DIFFICULTIES: tuple[Difficulty, ...] = (
    Difficulty(
        key="chill",
        label="Chill",
        detail="position",
        house_rules=False,
        well_guard=False,
        gravity_ms=850,
        blurb="Jev sees the well and where each piece would land. Nothing else — no preview "
        "of the result, no reading of the ground. It plays on shape alone.",
    ),
    Difficulty(
        key="steady",
        label="Steady",
        detail="board",
        house_rules=False,
        well_guard=False,
        gravity_ms=560,
        blurb="Every option now comes with a picture of the well it would leave behind. "
        "Jev picks from the pictures; the code accepts the pick as given.",
    ),
    Difficulty(
        key="ruthless",
        label="Ruthless",
        detail="fit",
        house_rules=True,
        well_guard=False,
        gravity_ms=340,
        blurb="Code reads the ground — shelves, slots, cliffs, trapped cells — and says what "
        "it found in words, plus how each landing would sit on it. When Jev calls the well "
        "dangerous, the house rules re-rank its own probabilities.",
    ),
    Difficulty(
        key="grandmaster",
        label="Grandmaster",
        detail="insight",
        house_rules=True,
        well_guard=True,
        gravity_ms=280,
        blurb="Two plies. Every landing also says what the next piece could do afterwards, "
        "and the rows closest to completing are named. While Jev says a slot is being held "
        "open, the house rules stop anything but a four-row clear from filling it.",
    ),
)

BY_KEY = {level.key: level for level in DIFFICULTIES}
DEFAULT = "grandmaster"


def difficulty(key: str | None) -> Difficulty:
    return BY_KEY.get((key or DEFAULT).lower(), BY_KEY[DEFAULT])


# ---------------------------------------------------------------- house rules
#
# Ruthless and Grandmaster run these, and they only ever reshuffle Jev's own
# probabilities using Jev's own answers -- a landing Jev thinks is hopeless
# cannot win on a bonus. The slot guard is Grandmaster's alone.

CLEAR_BONUS = 0.26  # for a four-row clear; a single is worth a sixteenth of it
WELL_GUARD = 0.30  # cost of filling the slot Jev says is being held open
GAP_PENALTY = 0.14  # per empty cell sealed under the piece, worse when in danger
HEIGHT_CEILING = 12  # rows; above this, extra height starts to cost
HEIGHT_PENALTY = 0.04
TORN = 0.25  # confidence below this and Jev is genuinely undecided
SURE = 0.60  # confidence above this and the piece goes down hard, no second thoughts


@dataclass
class Decision:
    """One move, and the reasoning the scoreboard gets to show off."""

    landing: Landing
    spot: str
    picked_by_jev: str
    probabilities: dict[str, float]
    confidence: float
    danger: float
    danger_level: str
    clear_now: float
    mood: str
    overruled: bool = False
    note: str = ""
    guarding: int | None = None
    keep_slot: float | None = None
    usage: dict = field(default_factory=dict)
    model: str = ""

    @property
    def torn(self) -> bool:
        return self.confidence < TORN

    @property
    def sure(self) -> bool:
        """Confident enough to slam it: an overruled pick is never that confident."""
        return self.confidence >= SURE and not self.overruled


def _adjust(
    landing: Landing,
    probability: float,
    danger: float,
    clear_now: float,
    slot: int | None = None,
) -> float:
    """Jev's probability, nudged by what Jev said about the state of the well.

    The clear bonus is square rather than linear, because the game pays that way:
    four rows at once are worth 800 and four rows one at a time are worth 400, so
    a single row should not outbid the shape that sets up a bigger one.
    """
    pressure = danger / 4.0
    score = probability
    if landing.rows_cleared:
        score += CLEAR_BONUS * clear_now * (landing.rows_cleared / 4.0) ** 2
    score -= GAP_PENALTY * landing.new_gaps * (1.0 + pressure)
    score -= HEIGHT_PENALTY * max(0, landing.tallest_after - HEIGHT_CEILING) * pressure
    if slot is not None and any(x == slot for x, _ in landing.cells):
        # Filling the slot costs less the more rows it takes; a four-row clear
        # is what the slot was being kept for, so that one is free.
        score -= WELL_GUARD * (1.0 - landing.rows_cleared / 4.0)
    return score


def decide(
    menu: dict[str, Landing],
    answers,
    level: Difficulty,
    model: str = "",
    usage: dict | None = None,
    slot: int | None = None,
    who: str = "Jev",
) -> Decision:
    """Turn five typed answers into one move.

    `who` is the player whose answers these are, so an overrule names it.
    """
    landing_answer = answers["landing"]
    probabilities = dict(landing_answer.probabilities)
    picked = landing_answer.choice
    danger = answers["danger"].score
    clear_now = answers["clear_now"].noul
    legend = answers["danger"].legend
    nearest = int(round(danger))

    decision = Decision(
        landing=menu[picked],
        spot=picked,
        picked_by_jev=picked,
        probabilities=probabilities,
        confidence=landing_answer.confidence,
        danger=danger,
        danger_level=legend.get(nearest) or legend.get(str(nearest), "—"),
        clear_now=clear_now,
        mood=answers["mood"].choice,
        model=model,
        usage=usage or {},
    )

    if not level.house_rules:
        return decision

    # The slot is only worth defending while Jev says so and the well is not
    # about to lose: survival first, then the four-row payday.
    keep = answers.get("keep_the_slot")
    if keep is not None:
        decision.keep_slot = keep.noul
    wanted = keep.noul if keep is not None else 0.0
    guarding = slot if level.well_guard and wanted > 0.5 and danger < 3.0 else None
    decision.guarding = guarding

    ranked = sorted(
        menu.items(),
        key=lambda item: _adjust(
            item[1], probabilities.get(item[0], 0.0), danger, clear_now, guarding
        ),
        reverse=True,
    )
    best, landing = ranked[0]
    if best != picked:
        decision.landing = landing
        decision.spot = best
        decision.overruled = True
        decision.note = _why(menu[picked], landing, danger, clear_now, guarding, who)
    return decision


def _why(
    rejected: Landing,
    taken: Landing,
    danger: float,
    clear_now: float,
    slot: int | None = None,
    who: str = "Jev",
) -> str:
    """Name the rule that moved the piece, so the overrule is never a mystery."""
    if slot is not None and any(x == slot for x, _ in rejected.cells):
        return (
            f"house rules: {who}'s pick would have filled column {slot + 1}, "
            "the slot it says is being kept open for a four-row clear"
        )
    if taken.rows_cleared > rejected.rows_cleared and clear_now > 0.5:
        rows = "row" if taken.rows_cleared == 1 else "rows"
        takes = f"{taken.rows_cleared} {rows}"
        return f"house rules: {who} wants a clear now, and this one takes {takes}"
    if taken.new_gaps < rejected.new_gaps:
        sealed = rejected.new_gaps - taken.new_gaps
        cells = "cell" if sealed == 1 else "cells"
        return f"house rules: {who}'s pick would have sealed {sealed} more {cells} under the piece"
    if taken.tallest_after < rejected.tallest_after:
        return (
            f"house rules: danger at {danger:.1f}/4, and this keeps the stack "
            f"{rejected.tallest_after - taken.tallest_after} rows lower"
        )
    return "house rules: a close call re-ranked under pressure"

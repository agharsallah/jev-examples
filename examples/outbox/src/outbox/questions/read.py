"""Pass one, assembled: every question and the state they are asked about."""

from __future__ import annotations

from typesafe_sdk import Choice, Question, Score

from .checks import CHECKS, SPECULATIVE
from .choices import INTENTS, RISKS
from .dimensions import DIMENSIONS


def read_docket() -> dict[str, Question]:
    """Pass one: every question the desk might need, in one request."""
    docket: dict[str, Question] = {
        "intent": Choice(
            instructions="What is `draft` trying to do?",
            criteria=INTENTS,
        ),
        "biggest_risk": Choice(
            instructions="If `draft` is sent as written, what is most likely to go wrong?",
            criteria=RISKS,
        ),
    }
    for name, (instructions, levels) in DIMENSIONS.items():
        docket[name] = Score(instructions=instructions, criteria=levels)
    docket.update(CHECKS)
    docket.update(SPECULATIVE)
    return docket


def read_state(draft: str, *, to: str | None, goal: str | None, channel: str | None) -> dict:
    """The draft, plus the few facts that change how it should be judged.

    These are separate fields rather than being glued onto the draft, so that a
    question can point at one of them by name and Jev knows which part of the
    state it is being asked about.
    """
    state: dict[str, object] = {"draft": draft}
    if to:
        state["reader"] = to
    if goal:
        state["what_the_sender_wants"] = goal
    if channel:
        state["channel"] = channel
    return state

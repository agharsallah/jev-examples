"""What each reader wants, expressed as numbers this code can weigh.

This is the composite-scoring pattern with one twist. The usual version weights
every dimension and treats higher as better. Here, higher is not better: a
draft can be too warm, too formal, too blunt, too short. So each audience gives
every dimension a *band* it should land in and a weight saying how much missing
that band matters.

Nothing here touches the network. Jev says where the draft landed; these tables
say what that means for the person receiving it, and they are yours to argue
with. Changing an audience re-scores an existing review with no new request,
which is exactly what the audience selector in the web UI does.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Below this confidence, a dimension is reported but left out of the score.
# Jev is saying it cannot read this one, and averaging a guess into a number
# people will act on is how a calibrated model gets turned back into a vibe.
UNSURE = 0.3


@dataclass(frozen=True)
class Band:
    """The stretch of a 0-4 scale this reader is happy with."""

    low: float
    high: float
    weight: float

    def miss(self, score: float) -> float:
        """How far outside the band the draft landed, in scale points."""
        if score < self.low:
            return self.low - score
        if score > self.high:
            return score - self.high
        return 0.0


@dataclass(frozen=True)
class Audience:
    key: str
    label: str
    wants: str
    bands: dict[str, Band]


def _audience(key: str, label: str, wants: str, **bands: tuple[float, float, float]) -> Audience:
    return Audience(
        key=key,
        label=label,
        wants=wants,
        bands={name: Band(*values) for name, values in bands.items()},
    )


# (low, high, weight) per dimension. The bands are opinions, held lightly.
AUDIENCES: dict[str, Audience] = {
    "manager": _audience(
        "manager",
        "a manager",
        "the point first, the ask second, and no archaeology",
        clarity=(3.0, 4.0, 3.0),
        actionability=(3.0, 4.0, 3.0),
        directness=(2.8, 4.0, 2.5),
        warmth=(2.0, 3.5, 1.0),
        formality=(1.5, 3.0, 1.0),
        brevity=(2.0, 3.5, 2.0),
    ),
    "teammate": _audience(
        "teammate",
        "a teammate",
        "enough context to act, without the ceremony",
        clarity=(2.5, 4.0, 2.0),
        actionability=(2.5, 4.0, 2.0),
        directness=(2.5, 4.0, 2.0),
        warmth=(2.0, 4.0, 1.5),
        formality=(0.5, 2.5, 1.0),
        brevity=(2.0, 4.0, 1.5),
    ),
    "client": _audience(
        "client",
        "a client",
        "certainty, courtesy, and nothing they have to chase",
        clarity=(3.0, 4.0, 3.0),
        actionability=(3.0, 4.0, 2.5),
        directness=(2.0, 3.5, 2.0),
        warmth=(2.5, 4.0, 2.0),
        formality=(2.0, 3.5, 2.0),
        brevity=(2.0, 3.5, 1.5),
    ),
    "exec": _audience(
        "exec",
        "an exec",
        "the decision, the number, and the door",
        clarity=(3.5, 4.0, 3.0),
        actionability=(3.0, 4.0, 2.0),
        directness=(3.0, 4.0, 3.0),
        warmth=(1.5, 3.0, 1.0),
        formality=(1.5, 3.0, 1.0),
        brevity=(3.0, 4.0, 3.0),
    ),
    "public": _audience(
        "public",
        "a public channel",
        "to be quotable out of context without embarrassing you",
        clarity=(3.0, 4.0, 3.0),
        actionability=(2.0, 4.0, 1.0),
        directness=(2.5, 4.0, 2.0),
        warmth=(2.5, 4.0, 2.0),
        formality=(2.0, 3.5, 2.0),
        brevity=(2.5, 4.0, 2.0),
    ),
    "friend": _audience(
        "friend",
        "a friend",
        "to sound like you, not like a status update",
        clarity=(2.0, 4.0, 1.5),
        actionability=(1.0, 4.0, 1.0),
        directness=(2.0, 4.0, 1.0),
        warmth=(3.0, 4.0, 2.5),
        formality=(0.0, 2.0, 1.5),
        brevity=(1.5, 4.0, 1.0),
    ),
}

DEFAULT_AUDIENCE = "teammate"

# Words in a free-text reader field that give the audience away, so `--to "my
# skip-level"` does not have to be spelled as one of the six keys.
HINTS: dict[str, tuple[str, ...]] = {
    "manager": ("manager", "boss", "lead", "supervisor", "skip-level", "skip level"),
    "exec": ("ceo", "cto", "cfo", "coo", "vp", "exec", "founder", "board", "director", "head of"),
    "client": ("client", "customer", "vendor", "supplier", "partner", "stakeholder", "account"),
    "public": ("public", "channel", "everyone", "all-hands", "announcement", "blog", "#"),
    "friend": ("friend", "mate", "buddy", "partner", "mum", "mom", "dad", "sister", "brother"),
    "teammate": ("teammate", "colleague", "team", "peer", "engineer", "designer", "squad"),
}


# Whole words only. Without this, "a teammate" matches the "mate" in the friend
# list and the draft gets scored for the pub.
def _mentions(text: str, hint: str) -> bool:
    if not hint[0].isalnum():
        return hint in text
    return re.search(rf"\b{re.escape(hint)}\b", text) is not None


def infer(reader: str | None) -> str:
    """Guess which set of bands applies from whatever the sender typed."""
    if not reader:
        return DEFAULT_AUDIENCE
    text = reader.casefold()
    for key in ("exec", "client", "public", "manager", "teammate", "friend"):
        if any(_mentions(text, hint) for hint in HINTS[key]):
            return key
    return DEFAULT_AUDIENCE


def resolve(key: str | None) -> Audience:
    return AUDIENCES.get((key or DEFAULT_AUDIENCE).casefold(), AUDIENCES[DEFAULT_AUDIENCE])

"""The shapes a review is made of: verdicts, findings, rails, the review itself.

Plain data. Deciding which finding fires or how far a rail missed happens in
the neighbouring modules; this one only says what the answer looks like.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..audience import Audience
from ..sentences import Sentence

SEND = "SEND IT"
TIGHTEN = "TIGHTEN IT"
REWRITE = "REWRITE IT"
HOLD = "DO NOT SEND"
UNCLEAR = "UNREADABLE"

VERDICT_BLURB = {
    SEND: "Nothing here is worth another pass.",
    TIGHTEN: "Send it after the fixes below; none of them are structural.",
    REWRITE: "The draft is working against you. Start from what you actually want.",
    HOLD: "Something in here should not leave your drafts folder as written.",
    UNCLEAR: "Jev could not tell what this message is for. That is usually the finding.",
}


@dataclass
class Finding:
    """One thing worth saying about the draft, with the number behind it."""

    key: str
    severity: str  # blocker | major | minor | good
    title: str
    fix: str
    value: float
    """The raw answer: a probability for a Noul, a 0-4 position for a Score."""
    strength: float
    """How strongly the answer supports this finding, always 0-1.

    A finding can fire on a low number as easily as a high one -- "no timing is
    given" is `has_deadline` at 0.06 -- so the raw value is the wrong thing to
    sort or display. This is the value turned the way the finding reads.
    """

    @property
    def is_good(self) -> bool:
        return self.severity == "good"


@dataclass
class Rail:
    """A dimension, where the draft landed, and where this reader wants it."""

    key: str
    label: str
    score: float
    confidence: float
    low: float
    high: float
    weight: float
    miss: float
    counted: bool
    level: str

    @property
    def verdict(self) -> str:
        if not self.counted:
            return "unsure"
        if self.miss == 0:
            return "in band"
        return "too low" if self.score < self.low else "too high"


@dataclass
class Review:
    draft: str
    audience: Audience
    verdict: str
    blurb: str
    fit: int
    """How close the draft sits to what this reader wants, 0-100, tone only."""
    send_score: int
    """`fit` after the findings are charged against it. The headline number."""
    intent: str
    intent_confidence: float
    intent_ranked: list[tuple[str, float]]
    risk: str
    risk_confidence: float
    rails: list[Rail]
    findings: list[Finding]
    sentences: list[Sentence] = field(default_factory=list)
    questions_asked: int = 0
    requests_made: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def problems(self) -> list[Finding]:
        return [f for f in self.findings if not f.is_good]

    @property
    def praise(self) -> list[Finding]:
        return [f for f in self.findings if f.is_good]

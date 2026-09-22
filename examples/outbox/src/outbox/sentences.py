"""Cutting a draft into sentences, and keeping track of where they were.

The offsets are the point. They let the web UI paint a finding onto the exact
run of characters Jev was asked about, instead of describing it in prose and
making the reader hunt for it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Abbreviations whose full stop does not end a sentence. Short list on purpose:
# a missed split costs a slightly long highlight, not a wrong answer.
ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "eg", "ie",
    "approx", "dept", "est", "fig", "no", "vol", "inc", "ltd", "co", "am", "pm",
}

_BOUNDARY = re.compile(r"(?<=[.!?…])[\"')\]]*\s+|\n{1,}")
_TRAILING_WORD = re.compile(r"([A-Za-z]+)\.[\"')\]]*\s*$")

# Long drafts are cut off rather than turned into a three-hundred question
# request. The first sixteen sentences are where the problems are anyway.
MAX_SENTENCES = 16


@dataclass
class Sentence:
    """One sentence, its place in the draft, and what Jev said about it."""

    index: int
    text: str
    start: int
    end: int
    probes: dict[str, float] = field(default_factory=dict)

    def flagged(self, thresholds: dict[str, float]) -> list[str]:
        """Probe names whose probability clears the bar set for them."""
        return [
            name
            for name, value in self.probes.items()
            if value >= thresholds.get(name, 0.6)
        ]


def split(draft: str) -> list[Sentence]:
    """Split on sentence ends and line breaks, keeping character offsets."""
    sentences: list[Sentence] = []
    start = 0
    cursor = 0
    for match in _BOUNDARY.finditer(draft):
        candidate = draft[start : match.start()]
        cursor = match.end()
        if _ends_on_abbreviation(candidate):
            continue
        _append(sentences, candidate, start)
        start = cursor
    _append(sentences, draft[start:], start)
    return sentences[:MAX_SENTENCES]


def _ends_on_abbreviation(candidate: str) -> bool:
    word = _TRAILING_WORD.search(candidate)
    return bool(word) and word.group(1).casefold() in ABBREVIATIONS


def _append(sentences: list[Sentence], raw: str, start: int) -> None:
    text = raw.strip()
    if not text:
        return
    offset = start + (len(raw) - len(raw.lstrip()))
    sentences.append(
        Sentence(index=len(sentences), text=text, start=offset, end=offset + len(text))
    )

"""The sentence pass, from the code's side: which probes to ask, what came back.

The questions themselves live in `questions/probes.py`. This module decides
which of them a draft has earned and folds the answers onto the sentences.
"""

from __future__ import annotations

from ..sentences import Sentence

# Which probes to spend a question on, and what each one means when it fires.
PROBE_TRIGGERS: dict[str, float] = {
    "carries_the_ask": 0.55,
    "barbed": 0.40,
    "hedged": 0.55,
    "ambiguous": 0.55,
    "sensitive": 0.35,
}

PROBE_SOURCE = {
    "carries_the_ask": "has_explicit_ask",
    "barbed": "passive_aggressive",
    "hedged": "hedged",
    "ambiguous": "could_be_read_two_ways",
    "sensitive": "sensitive_info",
}

PROBE_LABELS = {
    "carries_the_ask": "the ask",
    "barbed": "reads as pointed",
    "hedged": "hedging",
    "ambiguous": "ambiguous",
    "sensitive": "sensitive",
    "cuttable": "could go",
}

# A sentence is only highlighted when Jev is fairly sure. "Could go" is the
# loosest, because being wrong about it costs the reader nothing.
PROBE_THRESHOLDS = {
    "carries_the_ask": 0.35,
    "barbed": 0.6,
    "hedged": 0.65,
    "ambiguous": 0.75,
    "sensitive": 0.5,
    "cuttable": 0.7,
}

# Which highlight wins when a sentence trips more than one probe: the worst one.
PROBE_ORDER = ["sensitive", "barbed", "ambiguous", "hedged", "carries_the_ask", "cuttable"]


def top_probe(sentence: Sentence) -> str | None:
    """The one highlight a sentence gets, or None if nothing cleared its bar."""
    flags = sentence.flagged(PROBE_THRESHOLDS)
    return next((p for p in PROBE_ORDER if p in flags), None)


def probes_for(answers) -> list[str]:
    """Pick the sentence-level questions worth asking about *this* draft.

    This is why the sentence pass is a second request rather than more
    questions in the first one: until the checklist comes back, there is no way
    to know which probes are worth the tokens.
    """
    chosen = []
    for probe, threshold in PROBE_TRIGGERS.items():
        answer = answers.get(PROBE_SOURCE[probe])
        if answer is not None and float(answer.noul) >= threshold:
            chosen.append(probe)
    return chosen


def attach(sentences: list[Sentence], answers) -> list[Sentence]:
    """Fold `s{index}__{probe}` answers back onto the sentences they were about."""
    for name, answer in answers.items():
        index, _, probe = name.partition("__")
        position = int(index[1:])
        if 0 <= position < len(sentences):
            sentences[position].probes[probe] = float(answer.noul)
    _winner_takes_all(sentences, "carries_the_ask")
    return sentences


def _winner_takes_all(sentences: list[Sentence], probe: str) -> None:
    """Keep the strongest sentence for a probe and clear the rest.

    There is one ask, so "which sentence is it" is a comparison between
    sentences rather than a threshold on each. Every sentence in a polite
    request leans a little towards yes; only the highest one is the answer.
    """
    ranked = [s for s in sentences if probe in s.probes]
    if not ranked:
        return
    best = max(ranked, key=lambda s: s.probes[probe])
    for sentence in ranked:
        if sentence is not best:
            sentence.probes[probe] = 0.0

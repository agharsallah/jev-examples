"""Pass two: one question per sentence, written once pass one has answered."""

from __future__ import annotations

from typesafe_sdk import Noul, Question

# Each probe is (question text, when to ask it). The predicate reads pass one's
# checklist, which is the whole reason this is a second request: the questions
# do not exist until the first answers come back.
SENTENCE_PROBES: dict[str, tuple[str, str]] = {
    "carries_the_ask": (
        "Does this sentence contain the main request the draft is making?",
        "has_explicit_ask",
    ),
    "barbed": (
        "Would this sentence land as passive-aggressive, sarcastic or accusatory?",
        "passive_aggressive",
    ),
    "hedged": (
        "Is this sentence weakened by hedging, apology or filler?",
        "hedged",
    ),
    "ambiguous": (
        "Would a reasonable reader be left unsure what this sentence refers to or asks for?",
        "could_be_read_two_ways",
    ),
    "sensitive": (
        "Does this sentence contain information that should not travel over this channel?",
        "sensitive_info",
    ),
}

CUTTABLE = "Could this sentence be deleted without costing the reader anything they need?"

# Jev is being asked about one sentence at a time while the whole draft sits in
# the state, so the question has to carry the sentence with it. An object does
# that: the sentence in one field, the fixed question in another.
def sentence_docket(sentences: list[str], probes: list[str]) -> dict[str, Question]:
    """One Noul per sentence per probe, all in a single request."""
    docket: dict[str, Question] = {}
    for index, sentence in enumerate(sentences):
        docket[f"s{index}__cuttable"] = Noul(
            instructions={"sentence": sentence, "question": CUTTABLE},
        )
        for probe in probes:
            question, _ = SENTENCE_PROBES[probe]
            docket[f"s{index}__{probe}"] = Noul(
                instructions={"sentence": sentence, "question": question},
            )
    return docket

"""Everything Jev is asked about a draft message.

Two passes. The first reads the whole draft in one request: what it is trying
to do, how it reads along six dimensions, and a checklist of yes/no findings.
The second pass exists only because it cannot be written until the first has
answered -- which sentence carries the ask depends on whether there is an ask.

Every question in a pass goes out in a single request. Jev reads the state once
and answers all of them in parallel, so twenty-four questions cost barely more
than one.
"""

from __future__ import annotations

from typesafe_sdk import Choice, Noul, NoulCriteria, Question, Score

# --------------------------------------------------------------------------
# Pass one: the read
# --------------------------------------------------------------------------

# What the draft is for. Descriptions are what Jev actually sees, so they have
# to separate the options from each other; the names alone do nothing.
INTENTS = {
    "request": "Asks the reader to do something, decide something, or hand something over",
    "inform": "Shares news, status or context with nothing required from the reader",
    "decline": "Says no to a request, an invitation, a deadline or a scope",
    "apologise": "Takes responsibility for something that went wrong",
    "escalate": "Raises a problem to get attention, urgency or a different outcome",
    "negotiate": "Proposes terms, dates, scope or price and expects a counter",
    "disagree": "Pushes back on a decision, opinion or plan the reader holds",
    "appreciate": "Thanks, praises or credits the reader",
    "vent": "Expresses frustration without asking for anything specific",
    "other": "None of the above fits",
}

# Not "what is wrong" but "what is most likely to go wrong once it is read".
RISKS = {
    "misread": "The reader takes a different meaning than the one intended",
    "offends": "The reader reads it as rude, cold, sarcastic or accusatory",
    "ignored": "The reader has nothing concrete to act on and it drifts",
    "overcommits": "The sender promises more than they meant to",
    "leaks": "It exposes information that should not travel this way",
    "spawns_a_meeting": "It is unclear enough that the reader will ask to talk instead",
    "nothing_much": "There is no notable risk in sending this",
}

# Each dimension is a spectrum, and the order of the list *is* the scale.
# For several of these the good answer is in the middle, not at the top: see
# AUDIENCES in audience.py, where each reader says which stretch it wants.
DIMENSIONS: dict[str, tuple[str, list[str]]] = {
    "clarity": (
        "After one read, how clear is it what `draft` is about?",
        [
            "The subject has to be guessed at",
            "The point is in there, buried under other material",
            "Clear after a second read",
            "Clear on one read",
            "Impossible to misunderstand",
        ],
    ),
    "actionability": (
        "After reading `draft`, how clearly does the reader know what to do next?",
        [
            "Nothing indicates what the reader should do",
            "Something is wanted, but not what, or not by whom",
            "The action is stated but the reader has to work out the details",
            "The action is stated plainly",
            "The action, the owner and the timing are all unmistakable",
        ],
    ),
    "directness": (
        "How directly does `draft` state its point?",
        [
            "The point is never actually stated",
            "Heavily softened; the reader must infer the point",
            "Stated, with cushioning around it",
            "Stated plainly and early",
            "Blunt to the point of abruptness",
        ],
    ),
    "warmth": (
        "How warm is the tone of `draft` towards the reader?",
        [
            "Cold or hostile",
            "Clipped and purely transactional",
            "Neutral and businesslike",
            "Friendly and considerate",
            "Effusive",
        ],
    ),
    "formality": (
        "How formal is the register of `draft`?",
        [
            "Slang, fragments, lower case throughout",
            "Casual, the way colleagues talk",
            "Everyday professional",
            "Formal business writing",
            "Legalistic or ceremonial",
        ],
    ),
    "brevity": (
        "How does the length of `draft` compare to what it has to say?",
        [
            "Far longer than the content justifies",
            "Padded; a third could go",
            "About right for the content",
            "Tight; nothing spare",
            "So short that context is missing",
        ],
    ),
}

# Yes/no findings. Some are problems, some are things whose absence is the
# problem; review.py decides which is which and what to say about it.
CHECKS: dict[str, Noul] = {
    "has_explicit_ask": Noul(
        instructions="Does `draft` contain an explicit request for the reader to do something?",
        criteria=NoulCriteria(
            true="States something the reader should do, decide, send or confirm",
            false="Nothing is asked of the reader, or the ask is only implied",
        ),
    ),
    "has_deadline": Noul(
        instructions="Does `draft` say when it needs to happen by?",
        criteria=NoulCriteria(
            true="Names a date, a time, or a bounded window such as 'by Friday'",
            false="No timing given, or only vague timing such as 'soon'",
        ),
    ),
    "has_context": Noul(
        instructions=(
            "Does `draft` give the reader enough background to act"
            " without asking a question first?"
        ),
        criteria=NoulCriteria(
            true="Names the thing being discussed and says enough about it to act on",
            false="Relies on shared context the reader may not have",
        ),
    ),
    "passive_aggressive": Noul(
        instructions="Would a reader find `draft` passive-aggressive?",
        criteria=NoulCriteria(
            true="Pointed politeness, loaded reminders, or a complaint dressed as a question",
            false="Any frustration in it is stated openly, or there is none",
        ),
    ),
    "reads_as_angry": Noul(
        instructions="Would `draft` read as written in anger?",
    ),
    "blames_someone": Noul(
        instructions="Does `draft` assign fault to a named or implied person or team?",
    ),
    "over_apologises": Noul(
        instructions="Does `draft` apologise more than the situation calls for?",
        criteria=NoulCriteria(
            true="Apologies, self-deprecation or permission-seeking beyond what happened",
            false="No apology, or one that fits what happened",
        ),
    ),
    "hedged": Noul(
        instructions="Is the point of `draft` weakened by hedging?",
        criteria=NoulCriteria(
            true=(
                "'just', 'maybe', 'I might be wrong but', 'no rush'"
                " and similar qualifiers around the point"
            ),
            false="The point is stated without cushioning",
        ),
    ),
    "makes_commitment": Noul(
        instructions="Does the sender commit to doing something in `draft`?",
        criteria=NoulCriteria(
            true="Promises work, a date, a deliverable or an outcome",
            false="No promise is made",
        ),
    ),
    "sensitive_info": Noul(
        instructions="Does `draft` contain information that should not be sent this way?",
        criteria=NoulCriteria(
            true=(
                "Credentials, keys, personal data, salary, health, legal exposure,"
                " or unreleased confidential detail"
            ),
            false="Nothing beyond ordinary working information",
        ),
    ),
    "could_be_read_two_ways": Noul(
        instructions=(
            "Is there a sentence in `draft` that a reasonable reader"
            " could take two different ways?"
        ),
    ),
    "assumes_agreement": Noul(
        instructions=(
            "Does `draft` treat something as already agreed"
            " that the reader has not agreed to?"
        ),
    ),
}

# Speculative: each of these only matters for some intents. They go in the same
# request anyway, because an extra question is close to free and a second round
# trip is not. review.py ignores the ones that do not apply.
SPECULATIVE: dict[str, Question] = {
    "ask_is_self_contained": Noul(
        instructions=(
            "Could the reader act on the request in `draft`"
            " without replying to ask a question first?"
        ),
    ),
    "decline_is_final": Noul(
        instructions=(
            "Does `draft` make it clear that the answer is no,"
            " rather than leaving the door open?"
        ),
    ),
    "apology_repairs": Score(
        instructions="How well does the apology in `draft` repair the situation?",
        criteria=[
            "Apologises for the reader's reaction rather than the act",
            "Says sorry and stops there",
            "Says sorry and names what went wrong",
            "Names what went wrong and what happens next",
            "Names what went wrong, what happens next, and what prevents a repeat",
        ],
    ),
    "escalation_proportionate": Score(
        instructions="How well does the urgency of `draft` match the problem it describes?",
        criteria=[
            "Far more alarm than the problem warrants",
            "Somewhat overstated",
            "Proportionate",
            "Understated; the reader may not realise it matters",
            "So understated the problem reads as routine",
        ],
    ),
    "disagreement_stays_on_the_idea": Noul(
        instructions="Does the disagreement in `draft` stay on the idea rather than the person?",
    ),
}


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


# --------------------------------------------------------------------------
# Pass two: the sentence probes
# --------------------------------------------------------------------------

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

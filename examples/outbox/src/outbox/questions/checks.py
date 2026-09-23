"""Pass one, the checklist: yes/no findings, plus the speculative questions."""

from __future__ import annotations

from typesafe_sdk import Noul, NoulCriteria, Question, Score

# Yes/no findings. Some are problems, some are things whose absence is the
# problem; the review package decides which is which and what to say about it.
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
# trip is not. review/rules.py ignores the ones that do not apply.
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

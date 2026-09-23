"""Which answers become findings, and what the desk says when they do.

Tables rather than code, so that changing what counts as a problem is an edit
to a row: a threshold, a severity, a sentence. `findings.py` applies them.
"""

from __future__ import annotations

# (question, fires when the answer is "above"/"below", threshold, severity,
#  headline, what to do about it)
Rule = tuple[str, str, float, str, str, str]

CHECK_RULES: list[Rule] = [
    ("sensitive_info", "above", 0.6, "blocker",
     "There is something in here that should not travel this way",
     "Move the sensitive part to wherever it belongs and link to it instead."),
    ("reads_as_angry", "above", 0.65, "blocker",
     "This reads as written in anger",
     "It is a good draft. Send it tomorrow, or send the half of it that is about the work."),
    ("passive_aggressive", "above", 0.72, "blocker",
     "This lands as passive-aggressive",
     "Say the actual complaint in one plain sentence, or drop it."),
    ("passive_aggressive", "above", 0.55, "major",
     "Parts of this could read as pointed",
     "The highlighted sentences are doing it. Flatten them."),
    ("blames_someone", "above", 0.6, "major",
     "Someone is being blamed",
     "Describe what happened without the owner, unless the owner is the point."),
    ("hedged", "above", 0.6, "major",
     "The point is buried under hedging",
     "Cut 'just', 'maybe', 'I might be wrong' and 'no rush'. The point survives them."),
    ("over_apologises", "above", 0.6, "major",
     "There are more apologies than the situation earns",
     "Keep the first one. Delete the rest."),
    ("could_be_read_two_ways", "above", 0.75, "major",
     "At least one sentence can be taken two ways",
     "The highlighted sentence is the one. Pick the meaning you meant."),
    ("assumes_agreement", "above", 0.65, "minor",
     "It treats something as agreed that has not been agreed",
     "Ask for the agreement instead of assuming it; it costs one sentence."),
    ("makes_commitment", "above", 0.7, "minor",
     "You are committing to something",
     "Check you meant to. Once it is in writing it is a date."),
    ("has_context", "below", 0.35, "major",
     "The reader is missing context they need",
     "One line saying what this is about saves the round trip asking."),
    ("has_context", "above", 0.75, "good", "The reader has what they need to act", ""),
]

# Intents where the draft is asking for something. A missing ask is a finding
# for these and nothing at all for a decline or a thank-you, which is why the
# rule lives here rather than in CHECK_RULES.
ASK_INTENTS = ("request", "negotiate", "escalate")

ASK_RULES: list[Rule] = [
    ("has_explicit_ask", "below", 0.4, "major",
     "Nothing is actually asked",
     "Write the ask as a sentence starting with a verb, and put it near the top."),
    ("has_deadline", "below", 0.25, "minor",
     "No timing is given",
     "'By Thursday' turns a request into something the reader can schedule."),
    ("has_explicit_ask", "above", 0.75, "good", "The ask is explicit", ""),
    ("has_deadline", "above", 0.7, "good", "The timing is explicit", ""),
]

# Findings that only matter for one intent. They ride along in the same
# request as everything else and are ignored unless the intent turns up.
INTENT_RULES: dict[str, list[Rule]] = {
    "request": [
        ("ask_is_self_contained", "below", 0.4, "major",
         "The reader has to reply before they can help",
         "Add the missing piece -- the link, the number, the option list --"
         " so the first reply is the answer."),
    ],
    "decline": [
        ("decline_is_final", "below", 0.45, "major",
         "This does not read as a no",
         "If it is a no, say no in the first two sentences. A soft no is heard as a maybe."),
        ("decline_is_final", "above", 0.8, "good", "The no is unmistakable", ""),
    ],
    "disagree": [
        ("disagreement_stays_on_the_idea", "below", 0.5, "blocker",
         "The disagreement has moved onto the person",
         "Rewrite every sentence so the subject is the decision, not whoever made it."),
    ],
}

# Scored findings for the speculative Score questions, by intent. Same shape,
# but the threshold is a position on the 0-4 scale rather than a probability.
INTENT_SCORE_RULES: dict[str, list[Rule]] = {
    "apologise": [
        ("apology_repairs", "below", 2.0, "major",
         "The apology does not repair anything",
         "Name what went wrong and what happens next. Sorry on its own is for the sender."),
        ("apology_repairs", "above", 3.2, "good", "The apology does real work", ""),
    ],
    "escalate": [
        ("escalation_proportionate", "below", 1.3, "major",
         "The alarm is louder than the problem",
         "State the impact in one line and let the reader set the urgency."),
        ("escalation_proportionate", "above", 3.3, "major",
         "The problem is understated",
         "Say plainly what breaks and by when, or this gets filed as routine."),
    ],
}

RISK_LINES = {
    "misread": "Most likely failure: the reader takes a different meaning.",
    "offends": "Most likely failure: the reader reads this as rude.",
    "ignored": "Most likely failure: nothing happens.",
    "overcommits": "Most likely failure: you are held to more than you meant.",
    "leaks": "Most likely failure: this ends up somewhere it should not be.",
    "spawns_a_meeting": "Most likely failure: the reply is 'can we talk?'.",
    "nothing_much": "No particular failure mode stands out.",
}

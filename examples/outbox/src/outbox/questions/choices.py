"""Pass one, what the draft is for: the options for the two Choice questions."""

from __future__ import annotations

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

"""Drafts to try the desk on, chosen to land in different places.

`outbox demo` reviews all of them at once, which is also this example's answer to
"do I need one request per draft?" -- yes, because the states differ, but they
go out concurrently over one client.
"""

from __future__ import annotations

from .reviewer import Draft

SAMPLES: list[Draft] = [
    Draft(
        text=(
            "Hi Sam, just circling back on the migration doc from last week -- I know "
            "you're super busy, no rush at all!! Sorry to be a pain. I might be wrong "
            "but I think we agreed I'd take the write-up? Anyway it would be great to "
            "get your thoughts at some point if you get a chance. Happy to jump on a "
            "call if easier."
        ),
        to="my manager",
        goal="get the migration doc reviewed before Thursday",
        channel="email",
    ),
    Draft(
        text=(
            "Morning all. The checkout deploy is rolled back. Card payments failed for "
            "roughly 40 minutes starting 09:12; everything since has gone through. I am "
            "writing the incident note now and will post it here by 15:00. If you have "
            "a customer waiting on a refund from that window, send me the order id and "
            "I will handle it directly."
        ),
        to="the team channel",
        goal="tell everyone what happened and stop the questions",
        channel="slack",
    ),
    Draft(
        text=(
            "As per my previous email, the assets were due on the 14th. I'm sure it's "
            "just been a busy week for you. Let me know if the deadline we agreed is "
            "still realistic, or whether I should update the plan on my end. Happy to "
            "help if something is blocking you."
        ),
        to="our client at Northwind",
        goal="get the assets without losing the account",
        channel="email",
    ),
    Draft(
        text=(
            "Thanks for the offer -- I'm not going to take this one on. My next two "
            "weeks are committed to the billing migration and adding this would put "
            "both at risk. If it is still open in October I would be glad to pick it "
            "up then."
        ),
        to="a teammate",
        goal="say no without damage",
        channel="slack",
    ),
    Draft(
        text=(
            "quick one -- can you send me the prod db password again? the one in the "
            "shared doc doesn't work anymore. also here's the old one in case it helps: "
            "Hunter2-billing-prod. cheers"
        ),
        to="the platform team channel",
        goal="get back into the database",
        channel="slack",
    ),
    Draft(
        text=(
            "I have read the proposal and I don't think the approach works. Routing "
            "every write through the queue adds a failure mode we cannot observe, and "
            "the latency budget in section 3 assumes a cache hit rate we have never "
            "hit. I would like to walk through both points before we commit. Are you "
            "free Thursday afternoon?"
        ),
        to="the architecture review group",
        goal="stop the design being approved as written",
        channel="email",
    ),
]

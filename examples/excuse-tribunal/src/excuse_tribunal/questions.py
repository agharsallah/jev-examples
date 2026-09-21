"""The charges Jev is asked to rule on.

Every question in a docket goes to the API in a single request: Jev reads the
state once and evaluates all of them in parallel, which is both the cheap way
and the fast way to ask twelve things at once.
"""

from typesafe_sdk import Choice, Noul, NoulCriteria, Score

# Excuse archetypes. The descriptions are what Jev actually sees, so they have
# to separate the options from each other -- the names alone do nothing.
ARCHETYPES = {
    "the_classic": "A dog, a child, a houseplant or another dependent creature intervened",
    "blame_the_cloud": "Technology failed: an outage, a dead laptop, a sync that ate the work",
    "transit_saga": "Traffic, trains, planes, parking, or any other journey that went wrong",
    "body_betrayal": "Illness, injury, exhaustion, or a body that simply stopped cooperating",
    "calendar_crime": "A meeting, invite, timezone or reminder was wrong, missing or double-booked",
    "cosmic_forces": "Fate, astrology, vibes, bad luck, or the universe conspiring",
    "radical_honesty": "An admission of ordinary human failure with no external cause offered",
}

# Ordered from "survives nothing" to "survives anything". Score levels are
# positions on a spectrum, so the order of this list is the scale.
SURVIVAL_LEVELS = [
    "Would not survive a text message to a friend",
    "Survives a friend, but not a colleague",
    "Survives a colleague, but not a manager",
    "Survives a manager, but not a client",
    "Survives a client, a judge, and an audit",
]

BELIEVABILITY_LEVELS = [
    "Transparently invented",
    "Suspicious; the details do not hang together",
    "Plausible but unverifiable",
    "Convincing and internally consistent",
    "Carries specific, checkable detail a liar would not bother inventing",
]

EFFORT_LEVELS = [
    "Two words, typed while walking",
    "One sentence, minimal thought",
    "A considered paragraph",
    "A narrative with a beginning, a middle and an end",
    "An unsolicited thesis with exhibits",
]

DRAMA_LEVELS = [
    "Flat and factual",
    "Mildly inconvenienced",
    "Genuinely eventful",
    "Operatic",
    "Reads like the trailer for a disaster film",
]


def excuse_docket() -> dict:
    """The full set of charges for a human excuse."""
    return {
        "archetype": Choice(
            instructions="Which kind of excuse is this, judged by the reason it offers?",
            criteria=ARCHETYPES,
        ),
        "believability": Score(
            instructions="How believable is this excuse?",
            criteria=BELIEVABILITY_LEVELS,
        ),
        "survives_up_to": Score(
            instructions="Who is the most demanding audience this excuse could survive?",
            criteria=SURVIVAL_LEVELS,
        ),
        "effort": Score(
            instructions="How much effort went into constructing this excuse?",
            criteria=EFFORT_LEVELS,
        ),
        "drama": Score(
            instructions="How dramatic is the story being told?",
            criteria=DRAMA_LEVELS,
        ),
        "admits_fault": Noul(
            instructions="Does the speaker take any responsibility for what happened?",
            criteria=NoulCriteria(
                true="Accepts some blame, apologises, or names their own mistake",
                false="Responsibility is placed entirely outside the speaker",
            ),
        ),
        "blames_a_person": Noul(
            instructions="Is another named or implied person blamed for the failure?",
        ),
        "blames_a_machine": Noul(
            instructions="Is a device, network, app or other technology blamed?",
        ),
        "has_checkable_detail": Noul(
            instructions="Does the excuse contain a specific detail someone could verify?",
            criteria=NoulCriteria(
                true="Names a time, place, person, order number, flight, or other checkable fact",
                false="Only vague or unfalsifiable claims",
            ),
        ),
        "promises_a_fix": Noul(
            instructions="Does the speaker say what they will do about it?",
        ),
        "invokes_the_cosmos": Noul(
            instructions="Does the excuse appeal to fate, luck, astrology or the universe?",
        ),
        "suspiciously_rehearsed": Noul(
            instructions="Does this read like an excuse the speaker has given before?",
        ),
    }


COMMIT_QUALITY_LEVELS = [
    "Says nothing at all: 'fix', 'wip', 'stuff'",
    "Names a file or area, but not the change",
    "Says what changed, but not in a way a stranger could use",
    "Says what changed, clearly",
    "Says what changed and why, and the why is the interesting part",
]

CONFESSION_LEVELS = [
    "Serene; no distress detected",
    "Mild resignation",
    "Audible sighing",
    "Open despair",
    "A cry for help committed to version control",
]


def commit_docket() -> dict:
    """The charges for a git commit message on trial."""
    return {
        "archetype": Choice(
            instructions="What kind of commit message is this?",
            criteria={
                "the_classic": "Blames an outside force: a dependency, a tool, someone else's code",
                "blame_the_cloud": "Describes fighting infrastructure, CI, builds or environments",
                "calendar_crime": "Admits to rushing, a deadline, or a Friday deploy",
                "radical_honesty": "Plainly admits the author does not know why this works",
                "cosmic_forces": "Appeals to luck, magic, vibes or prayer",
                "body_betrayal": "Written by someone visibly out of energy",
                "professional": "A clean, ordinary, well-behaved commit message",
            },
        ),
        "believability": Score(
            instructions="How well does this message describe the change it claims to make?",
            criteria=COMMIT_QUALITY_LEVELS,
        ),
        "survives_up_to": Score(
            instructions="Who is the most demanding reviewer this message would survive?",
            criteria=[
                "Would not survive the author rereading it tomorrow",
                "Survives a teammate, barely",
                "Survives code review",
                "Survives a release audit six months later",
                "Survives a post-incident investigation",
            ],
        ),
        "effort": Score(
            instructions="How much care went into writing this message?",
            criteria=EFFORT_LEVELS,
        ),
        "drama": Score(
            instructions="How much emotional distress is on display in this message?",
            criteria=CONFESSION_LEVELS,
        ),
        "admits_fault": Noul(
            instructions="Does the message admit the author broke something?",
        ),
        "blames_a_person": Noul(
            instructions="Does the message blame another person or team?",
        ),
        "blames_a_machine": Noul(
            instructions="Does the message blame a tool, dependency, CI system or machine?",
        ),
        "has_checkable_detail": Noul(
            instructions="Does the message reference something specific and checkable?",
            criteria=NoulCriteria(
                true="Names an issue, ticket, function, file, version or error message",
                false="Only generic wording",
            ),
        ),
        "promises_a_fix": Noul(
            instructions="Does the message promise follow-up work later?",
        ),
        "invokes_the_cosmos": Noul(
            instructions="Does the message appeal to luck, magic or prayer?",
        ),
        "suspiciously_rehearsed": Noul(
            instructions="Does this look like a message the author writes over and over?",
        ),
    }

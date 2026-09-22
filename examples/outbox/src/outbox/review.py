"""What the numbers mean. No network calls live here.

Jev returns calibrated probabilities and scores. This module turns them into a
verdict a person can act on: which findings fire, how far the draft is from
what this particular reader wants, and whether the desk is confident enough to
say anything at all. All of it is ordinary Python you can read, test and
disagree with -- which is the part that stays yours.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .audience import UNSURE, Audience
from .questions import DIMENSIONS
from .sentences import Sentence

# Below this, Jev cannot tell what the draft is for -- which is almost always a
# fact about the draft rather than about the model.
INTENT_FLOOR = 0.45

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


# --------------------------------------------------------------------------
# Findings
# --------------------------------------------------------------------------

# key -> (fires when the probability is above/below, threshold, severity,
#         headline, what to do about it)
CHECK_RULES: list[tuple[str, str, float, str, str, str]] = [
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

ASK_RULES: list[tuple[str, str, float, str, str, str]] = [
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
INTENT_RULES: dict[str, list[tuple[str, str, float, str, str, str]]] = {
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

# Scored findings for the speculative Score questions, by intent:
# (question, "below"/"above", threshold, severity, headline, fix)
INTENT_SCORE_RULES: dict[str, list[tuple[str, str, float, str, str, str]]] = {
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


def _fires(value: float, direction: str, threshold: float) -> bool:
    return value > threshold if direction == "above" else value < threshold


def _collect(answers, rules, kind: str) -> list[Finding]:
    found: list[Finding] = []
    for key, direction, threshold, severity, title, fix in rules:
        answer = answers.get(key)
        if answer is None:
            continue
        value = float(answer.noul) if kind == "noul" else float(answer.score)
        if not _fires(value, direction, threshold):
            continue
        support = value if kind == "noul" else value / 4
        found.append(
            Finding(
                key=key,
                severity=severity,
                title=title,
                fix=fix,
                value=value,
                strength=support if direction == "above" else 1 - support,
            )
        )
    return found


def _dedupe(findings: list[Finding]) -> list[Finding]:
    """Keep the most severe finding per question; several rules can fire."""
    order = {"blocker": 0, "major": 1, "minor": 2, "good": 3}
    best: dict[str, Finding] = {}
    for finding in findings:
        current = best.get(finding.key)
        if current is None or order[finding.severity] < order[current.severity]:
            best[finding.key] = finding
    return sorted(best.values(), key=lambda f: (order[f.severity], -f.strength))


def rails_for(answers, audience: Audience) -> list[Rail]:
    """Where the draft landed on each dimension, against this reader's bands."""
    rails: list[Rail] = []
    for key in DIMENSIONS:
        answer = answers.get(key)
        band = audience.bands.get(key)
        if answer is None or band is None:
            continue
        score = float(answer.score)
        confidence = float(answer.confidence)
        rails.append(
            Rail(
                key=key,
                label=key.replace("_", " "),
                score=score,
                confidence=confidence,
                low=band.low,
                high=band.high,
                weight=band.weight,
                miss=band.miss(score),
                counted=confidence >= UNSURE,
                level=answer.legend.get(int(round(score)), ""),
            )
        )
    return rails


def fit_score(rails: list[Rail]) -> int:
    """0-100: how close the draft's tone sits to what this reader wants.

    A weighted average of how far each dimension missed its band, turned the
    right way up. Dimensions Jev was unsure about sit it out rather than
    dragging an invented number into the total.
    """
    counted = [rail for rail in rails if rail.counted]
    if not counted:
        return 0
    total_weight = sum(rail.weight for rail in counted)
    penalty = sum(rail.weight * min(rail.miss, 4.0) / 4.0 for rail in counted)
    return round(100 * (1 - penalty / total_weight))


# What each finding costs the headline score. A draft can be pitched perfectly
# for its reader and still not be sendable, which is why fit alone is not it.
SEVERITY_COST = {"blocker": 0, "major": 12, "minor": 4, "good": -3}

# However well the rest reads, a blocker caps the number here.
BLOCKER_CEILING = 25


def send_score(fit: int, findings: list[Finding]) -> int:
    """The headline number: fit, with the findings charged against it."""
    score = fit - sum(SEVERITY_COST[f.severity] for f in findings)
    if any(f.severity == "blocker" for f in findings):
        score = min(score, BLOCKER_CEILING)
    return max(0, min(100, score))


def _verdict(score: int, findings: list[Finding], intent_confidence: float) -> str:
    if intent_confidence < INTENT_FLOOR:
        return UNCLEAR
    if any(f.severity == "blocker" for f in findings):
        return HOLD
    if score >= 85:
        return SEND
    if score >= 60:
        return TIGHTEN
    return REWRITE


def assess(answers, audience: Audience, draft: str) -> Review:
    """Turn one System One response into a verdict for one reader."""
    intent = answers["intent"]
    risk = answers["biggest_risk"]

    findings = _collect(answers, CHECK_RULES, "noul")
    if intent.choice in ASK_INTENTS:
        findings += _collect(answers, ASK_RULES, "noul")
    findings += _collect(answers, INTENT_RULES.get(intent.choice, []), "noul")
    findings += _collect(answers, INTENT_SCORE_RULES.get(intent.choice, []), "score")
    findings = _dedupe(findings)

    rails = rails_for(answers, audience)
    fit = fit_score(rails)
    score = send_score(fit, findings)
    verdict = _verdict(score, findings, float(intent.confidence))

    return Review(
        draft=draft,
        audience=audience,
        verdict=verdict,
        blurb=VERDICT_BLURB[verdict],
        fit=fit,
        send_score=score,
        intent=intent.choice,
        intent_confidence=float(intent.confidence),
        intent_ranked=sorted(intent.probabilities.items(), key=lambda kv: -kv[1]),
        risk=risk.choice,
        risk_confidence=float(risk.confidence),
        rails=rails,
        findings=findings,
    )


def rescore(review: Review, audience: Audience) -> Review:
    """Re-run the verdict for a different reader, without asking Jev again.

    The scores did not change; what the reader wants did. This is the line the
    whole example is drawn around, so it is one function and no I/O.
    """
    rails = [
        Rail(
            key=rail.key,
            label=rail.label,
            score=rail.score,
            confidence=rail.confidence,
            low=band.low,
            high=band.high,
            weight=band.weight,
            miss=band.miss(rail.score),
            counted=rail.counted,
            level=rail.level,
        )
        for rail in review.rails
        if (band := audience.bands.get(rail.key)) is not None
    ]
    fit = fit_score(rails)
    score = send_score(fit, review.findings)
    verdict = _verdict(score, review.findings, review.intent_confidence)
    return Review(
        **{
            **review.__dict__,
            "audience": audience,
            "rails": rails,
            "fit": fit,
            "send_score": score,
            "verdict": verdict,
            "blurb": VERDICT_BLURB[verdict],
        }
    )


# --------------------------------------------------------------------------
# The sentence pass
# --------------------------------------------------------------------------

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

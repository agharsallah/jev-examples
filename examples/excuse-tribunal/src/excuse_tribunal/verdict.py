"""Sentencing. Jev supplies the judgments; the punishments are decided here.

This is the whole point of the pattern: the model returns calibrated numbers,
and ordinary Python decides what they mean. Nothing below calls the API, so the
tribunal's sense of humour is deterministic and testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Below this, Jev is telling us it genuinely cannot read the excuse. Guessing
# anyway would be the one unforgivable courtroom error.
MISTRIAL_CONFIDENCE = 0.5

SENTENCES = [
    "Coffee for the entire team, purchased in person, at a shop with a queue.",
    "You bring the snacks to the next retro. Good ones.",
    "You write the meeting notes for a week.",
    "One (1) sincere apology, delivered without the word 'but'.",
    "Time served. Do not do it again.",
]

RULINGS = {
    "guilty": "GUILTY OF FABRICATION",
    "suspicion": "RELEASED UNDER SUSPICION",
    "acquitted": "ACQUITTED",
    "mistrial": "MISTRIAL",
}


@dataclass
class Charge:
    """One yes/no finding, with the probability Jev put behind it."""

    label: str
    probability: float

    @property
    def upheld(self) -> bool:
        return self.probability >= 0.5


@dataclass
class Verdict:
    ruling: str
    headline: str
    sentence: str
    believability: float
    believability_confidence: float
    archetype: str
    archetype_confidence: float
    archetype_probabilities: dict[str, float]
    survives_up_to: float
    survival_legend: dict[int, str]
    effort: float
    drama: float
    aggravating: list[Charge] = field(default_factory=list)
    mitigating: list[Charge] = field(default_factory=list)
    remarks: list[str] = field(default_factory=list)

    @property
    def is_mistrial(self) -> bool:
        return self.ruling == RULINGS["mistrial"]


# Findings that count against the accused, and the line the clerk reads out.
AGGRAVATING = {
    "blames_a_person": "Blamed another human being",
    "blames_a_machine": "Blamed a machine that cannot defend itself",
    "invokes_the_cosmos": "Invoked the cosmos",
    "suspiciously_rehearsed": "Shows signs of prior use",
}

MITIGATING = {
    "admits_fault": "Accepted responsibility",
    "has_checkable_detail": "Offered a verifiable detail",
    "promises_a_fix": "Proposed a remedy",
}


def _charges(answers, spec: dict[str, str]) -> list[Charge]:
    found = []
    for key, label in spec.items():
        answer = answers.get(key)
        if answer is None:
            continue
        charge = Charge(label=label, probability=float(answer.noul))
        if charge.upheld:
            found.append(charge)
    return sorted(found, key=lambda c: c.probability, reverse=True)


def _headline(believability: float, aggravating: int, mitigating: int) -> str:
    if believability < 1.0:
        return "The court has heard better from a child."
    if believability < 2.0:
        return "The story does not survive contact with a second question."
    if believability < 3.0 and aggravating > mitigating:
        return "Plausible, but the accused points the finger too readily."
    if believability < 3.0:
        return "Plausible. Unproven. The court is watching."
    if believability >= 4.0 and mitigating:
        return "The rare excuse that is simply true."
    return "The court finds no fault with this account."


def _remarks(answers, believability: float, effort: float, drama: float) -> list[str]:
    remarks = []
    if drama - believability >= 1.5:
        remarks.append("Considerable drama, little substance. The court is not a theatre.")
    if effort >= 3.0 and believability < 2.0:
        remarks.append("Enormous effort spent on a story nobody believes. Redirect it.")
    if effort < 1.0 and believability >= 3.0:
        remarks.append("Barely any effort, and yet entirely credible. Suspicious in itself.")
    admits = answers.get("admits_fault")
    blames = answers.get("blames_a_person")
    if admits is not None and blames is not None and admits.noul < 0.2 and blames.noul > 0.8:
        remarks.append("Zero fault accepted, one human blamed. The arithmetic is noted.")
    return remarks


def deliberate(answers) -> Verdict:
    """Turn a System One response into a ruling and a sentence."""
    believability = answers["believability"]
    archetype = answers["archetype"]
    survival = answers["survives_up_to"]
    effort = answers["effort"]
    drama = answers["drama"]

    score = float(believability.score)
    confidence = float(believability.confidence)

    aggravating = _charges(answers, AGGRAVATING)
    mitigating = _charges(answers, MITIGATING)

    # Aggravating findings drag the sentence down, mitigating ones lift it.
    adjusted = score - 0.4 * len(aggravating) + 0.4 * len(mitigating)
    adjusted = max(0.0, min(4.0, adjusted))

    if confidence < MISTRIAL_CONFIDENCE:
        ruling = RULINGS["mistrial"]
        headline = "The excuse is too incoherent to judge. Jev declines to rule."
        sentence = "Case adjourned. Come back with a story that holds still."
    else:
        if adjusted < 1.5:
            ruling = RULINGS["guilty"]
        elif adjusted < 3.0:
            ruling = RULINGS["suspicion"]
        else:
            ruling = RULINGS["acquitted"]
        headline = _headline(score, len(aggravating), len(mitigating))
        sentence = SENTENCES[round(adjusted)]

    return Verdict(
        ruling=ruling,
        headline=headline,
        sentence=sentence,
        believability=score,
        believability_confidence=confidence,
        archetype=archetype.choice,
        archetype_confidence=float(archetype.confidence),
        archetype_probabilities=dict(archetype.probabilities),
        survives_up_to=float(survival.score),
        survival_legend=dict(survival.legend),
        effort=float(effort.score),
        drama=float(drama.score),
        aggravating=aggravating,
        mitigating=mitigating,
        remarks=_remarks(answers, score, float(effort.score), float(drama.score)),
    )

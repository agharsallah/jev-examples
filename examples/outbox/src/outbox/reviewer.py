"""Running a draft past the desk: one pass, then a second one if it is worth it.

The split between the two passes is deliberate and it is the only place in this
example where a second request is justified. Pass one asks everything that can
be asked about the draft as a whole. Pass two asks about individual sentences,
and *which* questions it asks depends on what pass one found -- there is no
point spending a question per sentence on hedging in a draft that does not
hedge. Everything else stays in one request.
"""

from __future__ import annotations

import asyncio
import statistics
from dataclasses import dataclass

from typesafe_sdk import ChoiceAnswer, ScoreAnswer, SystemOneResponse

from . import audience as audiences
from . import desk
from .questions import read_docket, read_state, sentence_docket
from .review import Review, assess, attach, probes_for
from .sentences import split


class Read(SystemOneResponse):
    """The answers this code cannot run without, as typed attributes.

    Passing a response model to `system_one` moves the failure forward: if one
    of these does not come back, the request fails here instead of raising a
    KeyError three modules later. Everything else still arrives in `.answers`.
    """

    intent: ChoiceAnswer
    biggest_risk: ChoiceAnswer
    clarity: ScoreAnswer
    actionability: ScoreAnswer
    directness: ScoreAnswer
    warmth: ScoreAnswer
    formality: ScoreAnswer
    brevity: ScoreAnswer


@dataclass(frozen=True)
class Draft:
    """A draft and the handful of facts that change how it should be judged."""

    text: str
    to: str | None = None
    goal: str | None = None
    channel: str | None = None

    @property
    def state(self) -> dict:
        return read_state(self.text, to=self.to, goal=self.goal, channel=self.channel)


def review(
    draft: Draft,
    *,
    audience_key: str | None = None,
    model: str | None = None,
    deep: bool = True,
) -> Review:
    """Review one draft. One request, or two when the sentence pass earns it."""
    docket = read_docket()
    response = desk.ask(draft.state, docket, model=model, response_model=Read)

    reader = audiences.resolve(audience_key or audiences.infer(draft.to))
    result = assess(response.answers, reader, draft.text)
    result.questions_asked = len(docket)
    result.requests_made = 1
    result.input_tokens = response.usage.input_tokens or 0
    result.output_tokens = response.usage.output_tokens or 0

    if deep:
        _sentence_pass(draft, response, result, model=model)
    return result


def _sentence_pass(draft: Draft, response, result: Review, *, model: str | None) -> None:
    """Ask about each sentence, using the probes pass one made relevant."""
    sentences = split(draft.text)
    probes = probes_for(response.answers)
    if not sentences or (len(sentences) < 2 and not probes):
        return

    docket = sentence_docket([s.text for s in sentences], probes)
    second = desk.ask(draft.state, docket, model=model)

    result.sentences = attach(sentences, second.answers)
    result.questions_asked += len(docket)
    result.requests_made += 1
    result.input_tokens += second.usage.input_tokens or 0
    result.output_tokens += second.usage.output_tokens or 0


# --------------------------------------------------------------------------
# A batch of drafts, and the same draft several times
# --------------------------------------------------------------------------


def review_all(drafts: list[Draft], *, model: str | None = None) -> list[Review]:
    """Review several drafts at once.

    Separate requests, because the states differ -- but concurrent ones, over
    one client. Questions about the same state belong in one request; questions
    about different states do not.
    """
    docket = read_docket()
    responses = asyncio.run(
        desk.ask_many([(d.state, docket) for d in drafts], model=model)
    )
    reviews = []
    for draft, response in zip(drafts, responses, strict=True):
        reader = audiences.resolve(audiences.infer(draft.to))
        result = assess(response.answers, reader, draft.text)
        result.questions_asked = len(docket)
        result.requests_made = 1
        result.input_tokens = response.usage.input_tokens or 0
        result.output_tokens = response.usage.output_tokens or 0
        reviews.append(result)
    return reviews


@dataclass
class Stability:
    """How much the desk's answers move when you ask it the same thing twice."""

    runs: int
    verdicts: dict[str, int]
    send_scores: list[int]
    wobbliest: list[tuple[str, float]]

    @property
    def agreement(self) -> float:
        return max(self.verdicts.values()) / self.runs if self.runs else 0.0

    @property
    def settled(self) -> bool:
        return self.agreement >= 0.8

    @property
    def spread(self) -> int:
        return max(self.send_scores) - min(self.send_scores) if self.send_scores else 0


def measure_stability(
    draft: Draft,
    *,
    runs: int = 5,
    audience_key: str | None = None,
    model: str | None = None,
) -> Stability:
    """Ask the same question several times and see whether the answer holds.

    A borderline draft is not the same thing as a confidently mediocre one, and
    the difference shows up here rather than in any single response. Cheap to
    check, because the runs go out concurrently.
    """
    docket = read_docket()
    responses = asyncio.run(
        desk.ask_many([(draft.state, docket)] * runs, model=model)
    )
    reader = audiences.resolve(audience_key or audiences.infer(draft.to))

    verdicts: dict[str, int] = {}
    scores: list[int] = []
    samples: dict[str, list[float]] = {}
    for response in responses:
        result = assess(response.answers, reader, draft.text)
        verdicts[result.verdict] = verdicts.get(result.verdict, 0) + 1
        scores.append(result.send_score)
        for name, answer in response.answers.items():
            value = _numeric(answer)
            if value is not None:
                samples.setdefault(name, []).append(value)

    wobbliest = sorted(
        ((name, statistics.pstdev(values)) for name, values in samples.items() if len(values) > 1),
        key=lambda pair: -pair[1],
    )[:5]
    return Stability(runs=runs, verdicts=verdicts, send_scores=scores, wobbliest=wobbliest)


def _numeric(answer) -> float | None:
    """One number per answer, so runs can be compared question by question."""
    if answer.type == "noul":
        return float(answer.noul)
    if answer.type == "score":
        return float(answer.score) / 4
    return float(max(answer.probabilities.values()))

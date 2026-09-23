"""Counterfactuals: take a piece of the evidence out and ask again.

A highlight says "this sentence reads like a bug report". A counterfactual
says "without this sentence, Jev is 0.34 sure it is a bug instead of 0.97" —
which is a claim about what actually drove the answer, measured rather than
narrated. Each removal is its own request (the state differs), all sent at
once, and each re-asks only the decision questions, not the whole docket.
"""

from __future__ import annotations

from . import jev, questions
from .taxonomy import Taxonomy

# The unit index that stands for the issue title.
TITLE = -1


def without(state: dict, body: str, units: list[dict], drop: set[int]) -> dict:
    """The same state with some units cut out of the body and the unit list."""
    kept = body
    for unit in sorted((u for u in units if u["index"] in drop), key=lambda u: -u["start"]):
        kept = kept[: unit["start"]] + kept[unit["end"] :]
    issue = dict(state["issue"])
    if TITLE in drop:
        # Titles often carry the answer outright ("[Bug] ..."); removing it
        # shows how much the body alone supports the call.
        issue["title"] = ""
    issue["body"] = kept
    issue["units"] = [u["text"] for u in units if u["asked"] and u["index"] not in drop]
    return {**state, "issue": issue}


def _target(answer: dict) -> tuple[str, float]:
    if answer["type"] == "choice":
        return answer["choice"], answer["probabilities"][answer["choice"]]
    return "score", answer["score"]


def counterfactuals(
    m: dict,
    state: dict,
    removals: list[list[int]],
    *,
    model: str | None = None,
) -> list[dict]:
    """For each set of units removed, how every decision moved.

    The 'before' numbers are the original answers: the decision questions are
    word for word the ones in the full request, and Jev answers each question
    independently of the others it was asked alongside.
    """
    tax = Taxonomy.from_dict(m["taxonomy"])
    docket = questions.decision_questions(tax)
    requests = [(without(state, m["body"], m["units"], set(drop)), docket) for drop in removals]
    readings = jev.ask_many(requests, model=model)

    results = []
    for drop, reading in zip(removals, readings, strict=True):
        if reading is None:
            continue
        moves = {}
        for key, before in m["answers"].items():
            if key not in docket:
                continue
            after = reading.answers[key]
            target, p_before = _target(before)
            if before["type"] == "choice":
                p_after = after["probabilities"].get(target, 0.0)
                flipped = after["choice"] != target
                moves[key] = {
                    "target": target,
                    "before": p_before,
                    "after": p_after,
                    "now": after["choice"],
                    "flipped": flipped,
                }
            else:
                moves[key] = {
                    "target": "score",
                    "before": p_before,
                    "after": after["score"],
                    "now": None,
                    "flipped": False,
                }
        results.append(
            {
                "removed": drop,
                "moves": moves,
                "input_tokens": reading.input_tokens,
                "cost_usd": reading.cost_usd,
                "latency_s": reading.latency_s,
            }
        )
    return results


def default_removals(evidence: list[dict], top: int = 3, floor: float = 0.6) -> list[list[int]]:
    """The strongest units one at a time, then all of them together."""
    strong = [e["index"] for e in evidence if e["p_target"] >= floor][:top]
    removals = [[i] for i in strong]
    if len(strong) > 1:
        removals.append(strong)
    return removals

"""One issue, start to finish: fetch, clean, ask once, decide.

The flow is ordinary code. Jev appears once per issue (plus once per repo for
the labels), and everything it returns is kept raw next to the verdict, so
the browser can show the numbers and rescore them without asking again.
"""

from __future__ import annotations

from dataclasses import asdict

from . import clean, duplicates, github, jev, policy, questions, taxonomy
from .github import Issue, Repo
from .taxonomy import Taxonomy

# Recent issues fetched once per repo: the duplicate corpus, and the scan queue.
CORPUS = 300


def read_repo(
    ref: str, *, model: str | None = None, refresh: bool = False
) -> tuple[Repo, Taxonomy]:
    repo = github.repo(ref, refresh=refresh)
    return repo, taxonomy.read_labels(repo, model=model)


def state_for(
    repo: Repo, issue: Issue, units: list[clean.Unit], body: str, candidates: list[Issue]
) -> dict:
    """What Jev sees. Note what is *not* here: the labels already on the issue,
    and every bot comment — both would hand it the answer it is meant to give."""
    return {
        "repository": {"name": repo.slug, "description": repo.description},
        "issue": {
            "title": issue.title,
            "body": body,
            "units": [u.text for u in units],
            "reporter_role": issue.association.lower(),
            "comments": clean.human_comments(issue),
        },
        "candidates": [duplicates.as_state(c) for c in candidates],
    }


def prepare(
    repo: Repo,
    tax: Taxonomy,
    issue: Issue,
    corpus: list[Issue],
    *,
    search: bool = True,
    evidence: bool = True,
):
    """Everything up to the request: cleaned text, units, candidates, questions."""
    body = clean.clean_text(issue.body)
    units = clean.split(body)
    asked = clean.asked_units(units) if evidence else []
    candidates = duplicates.shortlist(repo.slug, issue, corpus, search=search)
    state = state_for(repo, issue, asked, body, candidates)
    if not evidence:
        del state["issue"]["units"]
    docket = questions.docket(tax, asked, len(candidates), evidence=evidence)
    return body, units, asked, candidates, state, docket


def measurement(
    repo: Repo, tax: Taxonomy, issue: Issue, body, units, asked, candidates, reading
) -> dict:
    """The raw material of a verdict: enough to rescore with no network at all."""
    return {
        "repo": {"slug": repo.slug, "description": repo.description, "url": repo.url},
        "issue": {
            "number": issue.number,
            "title": issue.title,
            "url": issue.url,
            "state": issue.state,
            "author": issue.author,
            "association": issue.association,
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
            "labels": issue.labels,
            "comments": issue.comment_count,
        },
        "body": body,
        "units": [asdict(u) | {"asked": u in asked} for u in units],
        "candidates": [
            {
                "number": c.number,
                "title": c.title,
                "state": c.state.lower(),
                "url": c.url,
                "created_at": c.created_at,
            }
            for c in candidates
        ],
        "taxonomy": tax.to_dict() | {"reading": None},
        "answers": reading.answers,
        "usage": {
            "model": reading.model,
            "input_tokens": reading.input_tokens,
            "latency_s": reading.latency_s,
            "cost_usd": reading.cost_usd,
            "cached": reading.cached,
            "defanged": reading.defanged,
            "questions": len(reading.answers),
        },
    }


def verdict(m: dict, settings: dict | None = None) -> policy.Assessment:
    """Measurement in, assessment out. Pure; what /api/rescore calls."""
    return policy.assess(
        m["answers"],
        Taxonomy.from_dict(m["taxonomy"]),
        candidates=m["candidates"],
        units=[u for u in m["units"] if u["asked"]],
        existing=m["issue"]["labels"],
        settings=settings,
    )


def triage(
    ref: str,
    number: int | None = None,
    *,
    model: str | None = None,
    fresh: bool = False,
    search: bool = True,
) -> tuple[dict, policy.Assessment, dict]:
    """Triage one issue. Returns (measurement, assessment, raw request).

    `fresh` re-reads the issue from GitHub and asks Jev again; otherwise
    both come from disk when they are there."""
    repo, tax = read_repo(ref, model=model)
    issue = github.issue(ref, number, refresh=fresh)
    corpus = github.issues(ref, limit=CORPUS)
    body, units, asked, candidates, state, docket = prepare(repo, tax, issue, corpus, search=search)
    reading = jev.ask(state, docket, model=model, fresh=fresh)
    m = measurement(repo, tax, issue, body, units, asked, candidates, reading)
    raw = {"state": state, "questions": reading.questions}
    return m, verdict(m), raw

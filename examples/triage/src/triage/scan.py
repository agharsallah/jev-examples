"""Many issues at once: the queue a maintainer actually works through.

Each issue is still one request with every question; a scan just sends many
of them concurrently. Duplicates are searched only among the recent issues
already fetched (GitHub's search API is rate limited, and a scan would spend
the whole budget in a minute). Every answer is cached, so re-running a scan —
or rescoring it under new thresholds — costs nothing.
"""

from __future__ import annotations

import time
from dataclasses import asdict

from . import github, jev
from .github import Issue, Repo
from .taxonomy import Taxonomy
from .triage import CORPUS, measurement, prepare, read_repo, verdict


def trim(m: dict) -> dict:
    """A measurement without its evidence: small enough to ship a hundred of.

    The per-unit answers and the body only feed the highlights on the issue
    page; the verdict never reads them.
    """
    slim = {
        **m,
        "body": "",
        "units": [],
        "answers": {k: v for k, v in m["answers"].items() if not k.startswith("u")},
    }
    slim.pop("taxonomy", None)  # Shared by every issue in a scan; sent once beside them.
    return slim


def rescore(measurements: list[dict], taxonomy: dict, settings: dict | None = None) -> list[dict]:
    """A whole queue under new thresholds or weights. No network."""
    return [summary(m, verdict({**m, "taxonomy": taxonomy}, settings)) for m in measurements]


def summary(m: dict, a) -> dict:
    """One row of the queue."""
    kind = m["answers"]["kind"]
    return {
        "number": m["issue"]["number"],
        "title": m["issue"]["title"],
        "url": m["issue"]["url"],
        "state": m["issue"]["state"],
        "labels": m["issue"]["labels"],
        "kind": kind["choice"],
        "kind_confidence": kind["confidence"],
        "assessment": asdict(a),
    }


def _measure(
    repo: Repo,
    tax: Taxonomy,
    issues: list[Issue],
    corpus: list[Issue],
    *,
    model,
    on_progress,
    evidence: bool = True,
) -> tuple[list[dict], dict]:
    if on_progress:
        on_progress(0, len(issues))
    prepared = [
        prepare(repo, tax, issue, corpus, search=False, evidence=evidence) for issue in issues
    ]
    done = 0

    def tick(_reading) -> None:
        nonlocal done
        done += 1
        if on_progress:
            on_progress(done, len(issues))

    started = time.perf_counter()
    readings = jev.ask_many([(p[4], p[5]) for p in prepared], model=model, on_done=tick)
    elapsed = time.perf_counter() - started
    measurements, skipped = [], []
    for issue, (body, units, asked, candidates, _, _), reading in zip(
        issues, prepared, readings, strict=True
    ):
        if reading is None:
            skipped.append({"number": issue.number, "title": issue.title, "url": issue.url})
            continue
        measurements.append(measurement(repo, tax, issue, body, units, asked, candidates, reading))
    readings = [r for r in readings if r is not None]
    fresh = [r for r in readings if not r.cached]
    totals = {
        "issues": len(issues),
        "requests": len(readings),
        "fresh_requests": len(fresh),
        "questions": sum(len(r.answers) for r in readings),
        "input_tokens": sum(r.input_tokens for r in readings),
        "cost_usd": sum(r.cost_usd for r in readings),
        "wall_s": round(elapsed, 2),
        "mean_latency_s": round(sum(r.latency_s for r in readings) / max(1, len(readings)), 3),
        "defanged": sum(1 for r in readings if r.defanged),
        "skipped": skipped,
    }
    return measurements, totals


def scan(
    ref: str,
    *,
    limit: int = 100,
    model: str | None = None,
    settings: dict | None = None,
    on_progress=None,
    refresh: bool = False,
) -> dict:
    """Triage the most recent open issues. Returns rows, trimmed measurements, totals."""
    repo, tax = read_repo(ref, model=model, refresh=refresh)
    corpus = github.issues(ref, limit=max(CORPUS, limit), refresh=refresh)
    queue = github.issues(ref, limit=limit, state="open", refresh=refresh)
    measurements, totals = _measure(repo, tax, queue, corpus, model=model, on_progress=on_progress)
    rows = [summary(m, verdict(m, settings)) for m in measurements]
    return {
        "repo": repo.slug,
        "taxonomy": tax.to_dict() | {"reading": None},
        "rows": rows,
        "measurements": [trim(m) for m in measurements],
        "totals": totals,
    }

"""The whole backlog at once: every open issue, read, scored and linked.

This is the view a product owner or a maintainer planning a week wants: what
is ready to pick up, what a newcomer could take, what is waiting on a
decision, which issues are the same problem filed twice. Each issue is still
one request; the overview asks everything the issue page asks except the
per-sentence evidence, which is most of the questions and only feeds the
highlights.

Everything below the request is plain code: the composite scores are
weighted blends of Jev's answers with the weights written down here, the
flags are thresholds, ages are date arithmetic, and duplicate clusters are
formed in the browser from the pairwise answers, so their threshold is a knob.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from datetime import UTC, datetime

from . import github
from .jev import HOME, TriageError
from .policy import LANES
from .questions import NONE_FIT
from .scan import _measure
from .triage import CORPUS, read_repo, verdict

# The last overview of each repo, so opening the page shows it again without
# asking GitHub or Jev anything. Only a refresh replaces it.
SNAPSHOTS = HOME / "overview"

# The most a single overview will read. A repo with more open issues gets the
# newest this many; the page says so.
MAX_ISSUES = 1000

# Each composite is a weighted blend of normalised answers (0..1). The weights
# are the definition; the UI prints them next to the score.
READINESS = {
    "actionability": 0.40,
    "clarity": 0.25,
    "decided": 0.20,  # 1 - needs_decision
    "focused": 0.05,  # 1 - multiple_problems
    "reproducible": 0.10,  # has_repro_steps, for bugs; 1 for anything else
}
BEGINNER = {
    "newcomer": 0.55,
    "small": 0.25,  # 1 - scope
    "clarity": 0.20,
}

# Pairs worth sending to the page. Clusters are drawn from these with a
# threshold the reader controls, so keep anything that might clear it.
EDGE_SAME = 0.40
EDGE_RELATED = 0.60

_BEGINNER_LABEL = ("good first", "good-first", "beginner", "easy", "starter", "first-timers")


def _norm(answer: dict) -> float:
    return answer["score"] / max(1, answer["levels"] - 1)


def _noul(answers: dict, key: str, default: float = 0.0) -> float:
    answer = answers.get(key)
    return answer["noul"] if answer else default


def _blend(parts: dict[str, float], weights: dict[str, float]) -> float:
    total = sum(weights[k] for k in parts) or 1.0
    return sum(weights[k] * v for k, v in parts.items()) / total


def _days(since: str | None, now: datetime) -> int | None:
    if not since:
        return None
    then = datetime.fromisoformat(since.replace("Z", "+00:00"))
    return max(0, (now - then).days)


def scores(answers: dict) -> dict:
    """The composites, and their parts, for one issue."""
    is_bug = answers["kind"]["choice"] == "bug"
    readiness_parts = {
        "actionability": _norm(answers["actionability"]),
        "clarity": _norm(answers["clarity"]),
        "decided": 1 - _noul(answers, "needs_decision"),
        "focused": 1 - _noul(answers, "multiple_problems"),
        "reproducible": _noul(answers, "has_repro_steps") if is_bug else 1.0,
    }
    beginner_parts = {
        "newcomer": _norm(answers["newcomer"]) if "newcomer" in answers else 0.0,
        "small": 1 - _norm(answers["scope"]),
        "clarity": _norm(answers["clarity"]),
    }
    return {
        "readiness": _blend(readiness_parts, READINESS),
        "readiness_parts": readiness_parts,
        "beginner": _blend(beginner_parts, BEGINNER),
        "beginner_parts": beginner_parts,
    }


def _beginner_label(m: dict) -> tuple[str, float] | None:
    """The repo's own 'good first issue' label, if it has one, and Jev's Noul on it."""
    for family in m["taxonomy"]["families"]:
        if family["mode"] != "nouls":
            continue
        for i, name in enumerate(family["labels"]):
            if any(word in name.casefold() for word in _BEGINNER_LABEL):
                return name, _noul(m["answers"], f"lab__{family['key']}__{i}")
    return None


def _component(m: dict) -> tuple[str | None, float]:
    family = next((f for f in m["taxonomy"]["families"] if f["key"] == "component"), None)
    answer = m["answers"].get("fam__component") if family else None
    if not answer or answer["choice"] == NONE_FIT:
        return None, 0.0
    return answer["choice"], answer["probabilities"][answer["choice"]]


def row(m: dict, now: datetime) -> dict:
    """One issue as the overview sees it: numbers, flags, and where it is going."""
    a = verdict(m)
    answers = m["answers"]
    kind = answers["kind"]
    component, p_component = _component(m)
    composite = scores(answers)
    label = _beginner_label(m)
    on_it = set(m["issue"]["labels"])
    return {
        "number": m["issue"]["number"],
        "title": m["issue"]["title"],
        "url": m["issue"]["url"],
        "author": m["issue"]["author"],
        "labels": m["issue"]["labels"],
        "comments": m["issue"]["comments"],
        "age_days": _days(m["issue"]["created_at"], now),
        "idle_days": _days(m["issue"].get("updated_at"), now),
        "kind": kind["choice"],
        "kind_confidence": kind["confidence"],
        "component": component,
        "component_p": p_component,
        "lane": a.lane,
        "lanes": a.lanes,
        "priority": a.priority,
        **composite,
        "impact": _norm(answers["impact"]),
        "scope": _norm(answers["scope"]),
        "frustration": _norm(answers["frustration"]),
        "needs_decision": _noul(answers, "needs_decision"),
        "security": _noul(answers, "security_sensitive"),
        "low_effort": _noul(answers, "low_effort"),
        "waiting_on_reporter": _noul(answers, "waiting_on_reporter"),
        "fixed_in_thread": max(
            _noul(answers, "fixed_in_thread"), _noul(answers, "reporter_confirmed")
        ),
        "missing": a.missing,
        "beginner_label": label[0] if label else None,
        "beginner_label_p": label[1] if label else None,
        "suggested": [
            {"label": s["label"], "status": s["status"], "p": s["p"]}
            for s in a.labels
            if s["status"] != "unsure" and s["label"] not in on_it
        ],
        "drift": a.drift,
        "cost_usd": m["usage"]["cost_usd"],
    }


def edges(m: dict) -> list[dict]:
    """The pairwise duplicate answers worth keeping for this issue."""
    found = []
    for i, candidate in enumerate(m["candidates"]):
        same = _noul(m["answers"], f"dup__{i}__same")
        related = _noul(m["answers"], f"dup__{i}__related")
        if same >= EDGE_SAME or related >= EDGE_RELATED:
            found.append(
                {
                    "a": m["issue"]["number"],
                    "b": candidate["number"],
                    "b_title": candidate["title"],
                    "b_state": candidate["state"],
                    "b_url": candidate["url"],
                    "same": same,
                    "related": related,
                }
            )
    return found


def breakdown(rows: list[dict]) -> dict:
    """Counts the charts draw: component × kind, lanes, kinds."""
    by_component: dict[str, Counter] = {}
    for r in rows:
        by_component.setdefault(r["component"] or "(none fits)", Counter())[r["kind"]] += 1
    return {
        "component_kind": [
            {"component": name, "total": sum(c.values()), "kinds": dict(c)}
            for name, c in sorted(by_component.items(), key=lambda kv: -sum(kv[1].values()))
        ],
        "lanes": dict(Counter(r["lane"] for r in rows)),
        "kinds": dict(Counter(r["kind"] for r in rows)),
    }


def _snapshot_path(ref: str):
    owner, name, _ = github.parse(ref)
    return SNAPSHOTS / f"{owner}__{name}.json".lower()


def saved(ref: str) -> dict | None:
    """The last overview of this repo, as it was saved. No network."""
    try:
        return json.loads(_snapshot_path(ref).read_text())
    except (OSError, ValueError):
        return None


def _save(ref: str, result: dict) -> None:
    try:
        path = _snapshot_path(ref)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result))
    except OSError:
        pass  # Not saving it only means the next visit recomputes from the caches.


def overview(
    ref: str,
    *,
    limit: int | None = None,
    model: str | None = None,
    on_progress=None,
    refresh: bool = False,
) -> dict:
    """Read every open issue (up to `limit`) and assemble the whole picture.

    Without `refresh` everything comes from disk when it is there: GitHub's
    issues as last fetched, and Jev's answers to them. With it, GitHub is read
    again, and only issues whose text changed cost a new Jev request.
    """
    repo, tax = read_repo(ref, model=model, refresh=refresh)
    wanted = min(limit or repo.open_issues or MAX_ISSUES, MAX_ISSUES)
    if wanted < 1:
        raise TriageError(f"{repo.slug} has no open issues to read.")
    queue = github.issues(ref, limit=wanted, state="open", refresh=refresh)
    recent = github.issues(ref, limit=CORPUS, refresh=refresh)
    # Duplicates are looked for among every open issue plus the recent closed
    # ones: a new report of a fixed bug is worth knowing about.
    corpus = list({i.number: i for i in queue + recent}.values())
    measurements, totals = _measure(
        repo, tax, queue, corpus, model=model, on_progress=on_progress, evidence=False
    )
    now = datetime.now(UTC)
    rows = [row(m, now) for m in measurements]
    result = {
        "repo": {
            "slug": repo.slug,
            "url": repo.url,
            "description": repo.description,
            "open_issues": repo.open_issues,
            "read": len(rows),
        },
        "rows": rows,
        "edges": [e for m in measurements for e in edges(m)],
        "breakdown": breakdown(rows),
        "weights": {"readiness": READINESS, "beginner": BEGINNER},
        "lanes": LANES,
        "totals": totals,
        "saved_at": time.time(),
        "limit": limit,
    }
    _save(ref, result)
    return result

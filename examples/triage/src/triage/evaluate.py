"""How well does it agree with the people who already labelled these issues?

GitHub hands over a labelled dataset for free: every issue that already
carries a type, component or priority label. The issue is triaged with those
labels hidden from Jev (they are never in the state), and the family Choice is
compared to what is on the issue. All of the arithmetic is here, in code.

Three things come out of it:

- agreement per family, and a confusion matrix of where it differs;
- calibration: when Jev puts 0.8 on its pick, is the pick right ~80% of the
  time? That is what makes a threshold mean something;
- the coverage curve: raise the auto-apply bar and see how many issues still
  clear it, and how often those are right. This is the knob a maintainer sets.

"Agreement", not "accuracy": the existing labels are someone's judgment too
(on some repos, another bot's), and the disagreements list is as likely to
surface mislabelled issues as model mistakes.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from . import github
from .questions import NONE_FIT
from .scan import _measure, trim
from .taxonomy import Taxonomy
from .triage import CORPUS, read_repo

BINS = 10
THRESHOLDS = [round(i / 20, 2) for i in range(20)]


def _truth(labels: list[str], family) -> set[str]:
    return {name for name in labels if name in family.labels}


def family_report(family, measurements: list[dict]) -> dict | None:
    """Metrics for one Choice family over every issue that carries one of its labels."""
    rows = []
    for m in measurements:
        truth = _truth(m["issue"]["labels"], family)
        answer = m["answers"].get(f"fam__{family.key}")
        if not truth or not answer:
            continue
        pick = answer["choice"]
        p = answer["probabilities"].get(pick, 0.0)
        ranked = sorted(answer["probabilities"].items(), key=lambda kv: -kv[1])
        top2 = {name for name, _ in ranked[:2]}
        rows.append(
            {
                "number": m["issue"]["number"],
                "title": m["issue"]["title"],
                "url": m["issue"]["url"],
                "truth": sorted(truth),
                "pick": pick,
                "p": p,
                "confidence": answer["confidence"],
                "correct": pick in truth,
                "top2": bool(top2 & truth),
                "p_truth": max(answer["probabilities"].get(t, 0.0) for t in truth),
            }
        )
    if not rows:
        return None

    n = len(rows)
    correct = sum(r["correct"] for r in rows)
    abstained = sum(r["pick"] == NONE_FIT for r in rows)

    # Macro-F1 over the labels actually present, single-label issues only.
    single = [r for r in rows if len(r["truth"]) == 1]
    per_label = {}
    for label in family.labels:
        tp = sum(r["pick"] == label and r["truth"][0] == label for r in single)
        fp = sum(r["pick"] == label and r["truth"][0] != label for r in single)
        fn = sum(r["pick"] != label and r["truth"][0] == label for r in single)
        if tp + fn == 0:
            continue
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn)
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[label] = {"support": tp + fn, "precision": precision, "recall": recall, "f1": f1}
    macro_f1 = sum(v["f1"] for v in per_label.values()) / len(per_label) if per_label else None

    # Reliability: bin by the probability on the pick, compare to how often it was right.
    bins = defaultdict(list)
    for r in rows:
        bins[min(BINS - 1, int(r["p"] * BINS))].append(r)
    reliability = [
        {
            "bin": b,
            "lo": b / BINS,
            "hi": (b + 1) / BINS,
            "n": len(items),
            "mean_p": sum(i["p"] for i in items) / len(items),
            "accuracy": sum(i["correct"] for i in items) / len(items),
        }
        for b, items in sorted(bins.items())
    ]
    ece = sum(abs(x["mean_p"] - x["accuracy"]) * x["n"] for x in reliability) / n

    coverage = []
    for t in THRESHOLDS:
        kept = [r for r in rows if r["confidence"] >= t and r["pick"] != NONE_FIT]
        coverage.append(
            {
                "threshold": t,
                "coverage": len(kept) / n,
                "accuracy": (sum(r["correct"] for r in kept) / len(kept)) if kept else None,
            }
        )

    confusion = Counter((r["truth"][0], r["pick"]) for r in single)
    labels_seen = sorted(
        {r["truth"][0] for r in single} | {r["pick"] for r in single},
        key=lambda x: (x == NONE_FIT, x),
    )

    # The pairs it most often confuses. When one pair dominates, the labels
    # themselves are usually the problem: two descriptions a reader cannot
    # tell apart from the issue text.
    confusions = [
        {"truth": t, "pick": p, "n": count}
        for (t, p), count in confusion.most_common()
        if t != p and p != NONE_FIT
    ][:3]
    wrong = sum(1 for r in single if not r["correct"] and r["pick"] != NONE_FIT)

    disagreements = sorted(
        (r for r in rows if not r["correct"] and r["pick"] != NONE_FIT),
        key=lambda r: (-r["p"], r["p_truth"]),
    )

    return {
        "family": family.title,
        "key": family.key,
        "n": n,
        "agreement": correct / n,
        "top2": sum(r["top2"] for r in rows) / n,
        "abstained": abstained,
        "macro_f1": macro_f1,
        "per_label": per_label,
        "ece": ece,
        "reliability": reliability,
        "coverage": coverage,
        "confusion": {
            "labels": labels_seen,
            "cells": [[confusion.get((t, p), 0) for p in labels_seen] for t in labels_seen],
        },
        "confusions": confusions,
        "top_confusion_share": (confusions[0]["n"] / wrong) if confusions and wrong else 0.0,
        "disagreements": disagreements[:25],
    }


def evaluate(
    ref: str,
    *,
    limit: int = 150,
    model: str | None = None,
    on_progress=None,
    refresh: bool = False,
) -> dict:
    """Triage recent issues that already carry labels, and score the agreement."""
    repo, tax = read_repo(ref, model=model, refresh=refresh)
    corpus = github.issues(ref, limit=max(CORPUS, limit * 2), refresh=refresh)
    families = [f for f in tax.families if f.mode == "choice"]
    labelled = [i for i in corpus if any(_truth(i.labels, f) for f in families)][:limit]
    measurements, totals = _measure(
        repo, tax, labelled, corpus, model=model, on_progress=on_progress
    )
    return report(Taxonomy.from_dict(tax.to_dict()), measurements, totals, repo.slug)


def report(tax: Taxonomy, measurements: list[dict], totals: dict, slug: str) -> dict:
    families = [f for f in tax.families if f.mode == "choice"]
    return {
        "repo": slug,
        "taxonomy": tax.to_dict() | {"reading": None},
        "families": [r for f in families if (r := family_report(f, measurements))],
        "totals": totals,
        "measurements": [trim(m) for m in measurements],
    }

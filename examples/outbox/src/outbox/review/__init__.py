"""What the numbers mean. No network calls live here.

Jev returns calibrated probabilities and scores. This package turns them into a
verdict a person can act on: which findings fire, how far the draft is from
what this particular reader wants, and whether the desk is confident enough to
say anything at all. All of it is ordinary Python you can read, test and
disagree with -- which is the part that stays yours.

  model.py      the verdicts and the dataclasses a review is made of
  rules.py      the tables: which answer becomes which finding
  findings.py   applying those tables to one response
  scoring.py    rails, fit, send score, verdict
  verdict.py    assess() and rescore(), the two entry points
  probes.py     the sentence pass: which probes to ask, folding answers back
"""

from .findings import findings_for
from .model import (
    HOLD,
    REWRITE,
    SEND,
    TIGHTEN,
    UNCLEAR,
    VERDICT_BLURB,
    Finding,
    Rail,
    Review,
)
from .probes import (
    PROBE_LABELS,
    PROBE_ORDER,
    PROBE_SOURCE,
    PROBE_THRESHOLDS,
    PROBE_TRIGGERS,
    attach,
    probes_for,
    top_probe,
)
from .rules import ASK_INTENTS, ASK_RULES, CHECK_RULES, INTENT_RULES, INTENT_SCORE_RULES, RISK_LINES
from .scoring import (
    BLOCKER_CEILING,
    INTENT_FLOOR,
    SEVERITY_COST,
    fit_score,
    rails_against,
    rails_for,
    send_score,
    verdict_for,
)
from .verdict import assess, rescore

__all__ = [
    "ASK_INTENTS",
    "ASK_RULES",
    "BLOCKER_CEILING",
    "CHECK_RULES",
    "HOLD",
    "INTENT_FLOOR",
    "INTENT_RULES",
    "INTENT_SCORE_RULES",
    "PROBE_LABELS",
    "PROBE_ORDER",
    "PROBE_SOURCE",
    "PROBE_THRESHOLDS",
    "PROBE_TRIGGERS",
    "REWRITE",
    "RISK_LINES",
    "SEND",
    "SEVERITY_COST",
    "TIGHTEN",
    "UNCLEAR",
    "VERDICT_BLURB",
    "Finding",
    "Rail",
    "Review",
    "assess",
    "attach",
    "findings_for",
    "fit_score",
    "probes_for",
    "rails_against",
    "rails_for",
    "rescore",
    "send_score",
    "top_probe",
    "verdict_for",
]

"""The desk, in a terminal.

Nothing here decides anything; it only draws what the review package already
worked out.

  styles.py      the shared console, colours and glyphs, and the banner
  report.py      the full verdict for one draft
  summaries.py   consistency runs, a batch of drafts, the model list
"""

from .report import marked_draft, rail_bar, report
from .styles import banner, console
from .summaries import batch_report, models_report, stability_report

__all__ = [
    "banner",
    "batch_report",
    "console",
    "marked_draft",
    "models_report",
    "rail_bar",
    "report",
    "stability_report",
]

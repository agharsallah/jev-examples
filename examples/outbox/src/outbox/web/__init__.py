"""The desk, in a browser.

Two endpoints worth noticing. `/api/read` does what the CLI does: one request
to Jev, then a second for the sentences, then ordinary Python. `/api/rescore`
does not call Jev at all -- it takes the measurements from a review that has
already happened and re-runs the verdict for a different reader. That is the
whole argument of the example, wired to a row of buttons: the model measured
the draft once, and changing who is reading it is a code decision.

  schemas.py   what the browser sends
  payload.py   what it gets back, and the way back from that to a Review
  app.py       the routes and the static files
"""

from .app import STATIC, create_app
from .payload import desk_config, payload, rebuild

__all__ = ["STATIC", "app", "create_app", "desk_config", "payload", "rebuild"]

# `uvicorn outbox.web:app` still works, as it did when this was one module.
app = create_app()

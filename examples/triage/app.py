"""Entrypoint for hosting triage on Vercel.

Vercel looks for a FastAPI instance named `app` in `app.py` at the project
root. The package lives under `src/`, so put that on the path and hand over the
same app `triage serve` runs. Set TYPESAFE_API_KEY and GITHUB_TOKEN in the
project's environment variables; both stay on the server, as they do locally.
Only /tmp is writable there, so the caches live in it (and last as long as the
instance does).
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("TRIAGE_HOME", "/tmp/triage")
os.environ.setdefault("TRIAGE_SNAPSHOTS", "/tmp/triage/overview")
sys.path.insert(0, str(Path(__file__).parent / "src"))

from triage.web import app  # noqa: E402

__all__ = ["app"]

"""Entrypoint for hosting the arcade on Vercel.

Vercel looks for a FastAPI instance named `app` in `app.py` at the project
root. The package lives under `src/`, so put that on the path and hand over the
same app `duel serve` runs. Set TYPESAFE_API_KEY in the project's environment
variables; the key stays on the server exactly as it does locally.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from tetris_duel.web import app  # noqa: E402

__all__ = ["app"]

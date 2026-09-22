"""The one place that talks to Jev."""

from __future__ import annotations

import os

from dotenv import find_dotenv, load_dotenv
from typesafe_sdk import RetryPolicy, TypeSafeAPIError, TypeSafeClient, TypeSafeError

API_KEY_ENV = "TYPESAFE_API_KEY"

MISSING_KEY = (
    f"No {API_KEY_ENV} in the environment, so nobody is playing the left-hand board.\n"
    "  cp .env.example .env   and put your key in it\n"
    f"  (or export {API_KEY_ENV}=... ; keys live at https://console.typesafe.ai/keys)"
)


class EngineError(RuntimeError):
    """Anything that stops the match, phrased for a human."""


def load_env() -> None:
    """Read a .env, so the key can live in a file instead of your shell history.

    Looks upward from the working directory first, then from this file, which
    means the same .env at the repo root serves `uv run` from anywhere. Real
    environment variables always win.
    """
    for path in (find_dotenv(usecwd=True), find_dotenv()):
        if path:
            load_dotenv(path, override=False)


def ask(state, docket: dict, model: str | None = None):
    """Send the whole docket in one request and return the answers.

    One request per falling piece. Everything in the docket is evaluated
    against the same well in parallel, so the commentary and the danger reading
    ride along with the move for almost nothing.
    """
    load_env()
    if not os.environ.get(API_KEY_ENV, "").strip():
        raise EngineError(MISSING_KEY)

    kwargs = {"retry": RetryPolicy(max_retries=3, timeout=20.0)}
    if model:
        kwargs["model"] = model

    try:
        with TypeSafeClient(**kwargs) as client:
            return client.system_one(state=state, questions=docket)
    except TypeSafeAPIError as error:
        if error.status == 429:
            raise EngineError("Jev is oversubscribed (HTTP 429). Give it a second.") from error
        raise EngineError(
            f"Jev refused the move: HTTP {error.status} (request {error.request_id})."
        ) from error
    except TypeSafeError as error:
        raise EngineError(f"Could not reach Jev: {error}") from error

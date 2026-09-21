"""The one place that talks to Jev."""

from __future__ import annotations

import os

from dotenv import find_dotenv, load_dotenv
from typesafe_sdk import RetryPolicy, TypeSafeAPIError, TypeSafeClient, TypeSafeError

API_KEY_ENV = "TYPESAFE_API_KEY"

MISSING_KEY = (
    f"No {API_KEY_ENV} in the environment. The court cannot sit without a judge.\n"
    "  cp .env.example .env   and put your key in it\n"
    f"  (or export {API_KEY_ENV}=... ; keys live at https://console.typesafe.ai/keys)"
)


class TribunalError(RuntimeError):
    """Anything that stops the hearing, phrased for a human."""


def load_env() -> None:
    """Read a .env, so the key can live in a file instead of your shell history.

    Looks upward from the working directory first, then from this file, which
    means the same .env at the repo root serves `uv run` from anywhere. Real
    environment variables always win.
    """
    for path in (find_dotenv(usecwd=True), find_dotenv()):
        if path:
            load_dotenv(path, override=False)


def hear_case(state, docket: dict, model: str | None = None):
    """Send the whole docket in one request and return the answers.

    Jev reads the state once and evaluates every question against it in
    parallel, so a dozen charges cost barely more than one.
    """
    load_env()
    if not os.environ.get(API_KEY_ENV, "").strip():
        raise TribunalError(MISSING_KEY)

    kwargs = {"retry": RetryPolicy(max_retries=3, timeout=20.0)}
    if model:
        kwargs["model"] = model

    try:
        with TypeSafeClient(**kwargs) as client:
            response = client.system_one(state=state, questions=docket)
    except TypeSafeAPIError as error:
        if error.status == 429:
            raise TribunalError(
                "The court is oversubscribed (HTTP 429). Try again in a moment."
            ) from error
        raise TribunalError(
            f"The API refused the case: HTTP {error.status} (request {error.request_id})."
        ) from error
    except TypeSafeError as error:
        raise TribunalError(f"Could not reach the tribunal: {error}") from error

    return response

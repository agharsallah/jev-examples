"""The only module that talks to Jev.

Everything else in this package is ordinary Python over the numbers that come
back from here, which is the shape the whole example is arguing for.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping

from dotenv import find_dotenv, load_dotenv
from typesafe_sdk import (
    AsyncTypeSafeClient,
    Question,
    RetryPolicy,
    SystemOneResponse,
    TypeSafeAPIError,
    TypeSafeClient,
    TypeSafeError,
)

API_KEY_ENV = "TYPESAFE_API_KEY"

RETRY = RetryPolicy(max_retries=3, timeout=30.0)

MISSING_KEY = (
    f"No {API_KEY_ENV} in the environment, so there is nobody to read your draft.\n"
    "  cp .env.example .env   and put your key in it\n"
    f"  (or export {API_KEY_ENV}=... ; keys live at https://console.typesafe.ai/keys)"
)


class DeskError(RuntimeError):
    """Anything that stops a review, phrased for a human."""


def load_env() -> None:
    """Read a .env so the key can live in a file instead of your shell history.

    Looks upward from the working directory first, then from this file, so the
    same .env at the repo root serves `uv run` from anywhere. Real environment
    variables always win.
    """
    for path in (find_dotenv(usecwd=True), find_dotenv()):
        if path:
            load_dotenv(path, override=False)


def require_key() -> None:
    load_env()
    if not os.environ.get(API_KEY_ENV, "").strip():
        raise DeskError(MISSING_KEY)


def _translate(error: Exception) -> DeskError:
    if isinstance(error, TypeSafeAPIError):
        if error.status == 429:
            return DeskError("The desk is oversubscribed (HTTP 429). Try again in a moment.")
        if error.status == 401:
            return DeskError(f"That key was refused (HTTP 401). Check {API_KEY_ENV}.")
        return DeskError(
            f"The API refused the request: HTTP {error.status} (request {error.request_id})."
        )
    return DeskError(f"Could not reach the desk: {error}")


def ask(
    state,
    questions: Mapping[str, Question],
    *,
    model: str | None = None,
    response_model: type | None = None,
) -> SystemOneResponse:
    """One request, however many questions.

    Jev evaluates every question in the request against the same state, in
    parallel, so the cost of asking is in the questions rather than the calls.
    """
    require_key()
    kwargs = {"model": model} if model else {}
    try:
        with TypeSafeClient(retry=RETRY) as client:
            if response_model is not None:
                return client.system_one(
                    state, dict(questions), response_model=response_model, **kwargs
                )
            return client.system_one(state, dict(questions), **kwargs)
    except (TypeSafeAPIError, TypeSafeError) as error:
        raise _translate(error) from error


async def ask_many(
    requests: list[tuple[object, Mapping[str, Question]]],
    *,
    model: str | None = None,
) -> list[SystemOneResponse]:
    """Several independent requests at once, over one client.

    Used for two things: reviewing a batch of drafts, and running the same
    draft repeatedly to see how stable the answers are. Neither is a case for
    putting the questions in one request, because the *states* differ.
    """
    require_key()
    kwargs = {"model": model} if model else {}
    try:
        async with AsyncTypeSafeClient(retry=RETRY) as client:
            return list(
                await asyncio.gather(
                    *(client.system_one(state, dict(qs), **kwargs) for state, qs in requests)
                )
            )
    except (TypeSafeAPIError, TypeSafeError) as error:
        raise _translate(error) from error


def models() -> list[tuple[str, str, str]]:
    """Every model this key can send a draft to."""
    require_key()
    try:
        with TypeSafeClient(retry=RETRY) as client:
            listed = client.models.list()
    except (TypeSafeAPIError, TypeSafeError) as error:
        raise _translate(error) from error
    return [(m.name, m.release_date, m.description) for m in listed.models]

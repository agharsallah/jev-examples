"""The only module that talks to Jev.

Answers come back as plain dicts rather than SDK objects. That is deliberate:
the same dicts are cached on disk, shipped to the browser, sent back to be
rescored under new thresholds, and loaded from test fixtures, and none of
those should care that a network was ever involved.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from typesafe_sdk import (
    AsyncTypeSafeClient,
    Question,
    RetryPolicy,
    TypeSafeAPIError,
    TypeSafeClient,
    TypeSafeError,
)

API_KEY_ENV = "TYPESAFE_API_KEY"

RETRY = RetryPolicy(max_retries=4, timeout=60.0)

# Published input price for jev-1.13 (output tokens are free).
DOLLARS_PER_MTOK = 0.042

# Scans fan out over hundreds of issues; this keeps them under the rate limit
# without making anyone wait on a queue they can see.
CONCURRENCY = 8

HOME = Path(os.environ.get("TRIAGE_HOME", Path.home() / ".triage"))
CACHE = HOME / "jev"

MISSING_KEY = (
    f"No {API_KEY_ENV} in the environment, so there is nobody to read the issues.\n"
    "  cp .env.example .env   and put your key in it\n"
    f"  (or export {API_KEY_ENV}=... ; keys live at https://console.typesafe.ai/keys)"
)


class TriageError(RuntimeError):
    """Anything that stops a triage, phrased for a human."""


@dataclass
class Reading:
    """One request's worth of answers, plus what it cost to get them."""

    answers: dict[str, dict]
    model: str
    input_tokens: int
    latency_s: float
    cached: bool = False
    defanged: int = 0  # 0 as sent; 1 backticks as quotes; 2 code and links omitted
    state: object = None
    questions: dict[str, dict] = field(default_factory=dict)

    @property
    def cost_usd(self) -> float:
        return self.input_tokens / 1e6 * DOLLARS_PER_MTOK

    def to_dict(self) -> dict:
        return {
            "answers": self.answers,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "latency_s": self.latency_s,
            "cached": self.cached,
            "defanged": self.defanged,
            "cost_usd": self.cost_usd,
        }


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
        raise TriageError(MISSING_KEY)


def wire(questions: Mapping[str, Question]) -> dict[str, dict]:
    """The questions exactly as they go over the wire, for caching and for showing."""
    return {name: q.model_dump(mode="json") for name, q in questions.items()}


_FENCED = re.compile(r"```.*?(```|$)", re.DOTALL)
_INLINE = re.compile(r"`[^`\n]+`")
_URL = re.compile(r"https?://\S+")


def defang(value, level: int = 1):
    """The same text, made less alarming to the firewall in front of the API.

    Some issue text — shell one-liners, pasted commands, lots of URLs — is
    refused with HTTP 403 before it reaches the model: the firewall scores the
    whole request, and enough command-looking fragments add up. A refused
    request is retried, first with backticks as plain quotes (same meaning to
    Jev), then with code and links replaced by placeholders. The reading
    records which level it took, and the UI says so.
    """
    if isinstance(value, str):
        if level >= 2:
            value = _FENCED.sub("[code block omitted]", value)
            value = _INLINE.sub("[code]", value)
            value = _URL.sub("[link]", value)
        return value.replace("`", "'")
    if isinstance(value, list):
        return [defang(v, level) for v in value]
    if isinstance(value, dict):
        return {k: defang(v, level) for k, v in value.items()}
    return value


def _refused(error: Exception) -> bool:
    return isinstance(error, TypeSafeAPIError) and error.status == 403


def _key(state, questions: dict[str, dict], model: str | None) -> str:
    blob = json.dumps([state, questions, model or "default"], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


def _plain(answer) -> dict:
    """An SDK answer as the dict the rest of the package reads."""
    if answer.type == "noul":
        return {"type": "noul", "noul": float(answer.noul)}
    if answer.type == "choice":
        return {
            "type": "choice",
            "choice": answer.choice,
            "probabilities": {k: float(v) for k, v in answer.probabilities.items()},
            "confidence": float(answer.confidence),
        }
    return {
        "type": "score",
        "score": float(answer.score),
        "probabilities": {int(k): float(v) for k, v in answer.probabilities.items()},
        "levels": len(answer.legend),
        "confidence": float(answer.confidence),
    }


def _load(key: str) -> dict | None:
    path = CACHE / f"{key}.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _save(key: str, payload: dict) -> None:
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        (CACHE / f"{key}.json").write_text(json.dumps(payload))
    except OSError:
        pass  # A cache that cannot be written is just a slower run.


def _from_cache(payload: dict, state, questions: dict[str, dict]) -> Reading:
    answers = payload["answers"]
    for answer in answers.values():
        if answer["type"] == "score":  # JSON turned the level keys into strings.
            answer["probabilities"] = {int(k): v for k, v in answer["probabilities"].items()}
    return Reading(
        answers=answers,
        model=payload["model"],
        input_tokens=payload["input_tokens"],
        latency_s=payload["latency_s"],
        cached=True,
        defanged=int(payload.get("defanged", 0)),
        state=state,
        questions=questions,
    )


def _translate(error: Exception) -> TriageError:
    if isinstance(error, TypeSafeAPIError):
        if error.status == 429:
            return TriageError("Jev is oversubscribed (HTTP 429). Try again in a moment.")
        if error.status == 401:
            return TriageError(f"That key was refused (HTTP 401). Check {API_KEY_ENV}.")
        if error.status == 403:
            return TriageError(
                "The API's firewall refused this issue (HTTP 403), "
                "even with its code and links omitted."
            )
        return TriageError(
            f"The API refused the request: HTTP {error.status} (request {error.request_id})."
        )
    return TriageError(f"Could not reach Jev: {error}")


def _reading(response, started: float, state, questions: dict[str, dict]) -> Reading:
    return Reading(
        answers={name: _plain(a) for name, a in response.answers.items()},
        model=response.model,
        input_tokens=response.usage.input_tokens or 0,
        latency_s=round(time.perf_counter() - started, 3),
        state=state,
        questions=questions,
    )


def ask(
    state,
    questions: Mapping[str, Question],
    *,
    model: str | None = None,
    fresh: bool = False,
) -> Reading:
    """One request, however many questions.

    Jev evaluates every question against the same state, in parallel, so the
    cost of asking is in the questions rather than the calls. Identical
    requests are answered from disk unless `fresh` is set.
    """
    shaped = wire(questions)
    key = _key(state, shaped, model)
    if not fresh and (hit := _load(key)):
        return _from_cache(hit, state, shaped)

    require_key()
    kwargs = {"model": model} if model else {}
    started = time.perf_counter()
    defanged = 0
    try:
        with TypeSafeClient(retry=RETRY) as client:
            while True:
                try:
                    sent = defang(state, defanged) if defanged else state
                    response = client.system_one(sent, dict(questions), **kwargs)
                    break
                except TypeSafeAPIError as error:
                    if not _refused(error) or defanged == 2:
                        raise
                    defanged += 1
    except (TypeSafeAPIError, TypeSafeError) as error:
        raise _translate(error) from error
    reading = _reading(response, started, state, shaped)
    reading.defanged = defanged
    _save(key, reading.to_dict())
    return reading


async def ask_many_async(
    requests: list[tuple[object, Mapping[str, Question]]],
    *,
    model: str | None = None,
    fresh: bool = False,
    on_done=None,
) -> list[Reading | None]:
    """Independent requests at once, over one client, a few in flight at a time.

    Used when the *states* differ: one request per issue in a scan, or one per
    sentence removed in a counterfactual. Questions about one state always go
    in one request instead. A request that fails comes back as None, so one
    refused issue cannot sink the rest.
    """
    shaped = [(state, wire(qs)) for state, qs in requests]
    keys = [_key(state, qs, model) for state, qs in shaped]
    results: list[Reading | None] = [None] * len(requests)
    todo = []
    for i, (key, (state, qs)) in enumerate(zip(keys, shaped, strict=True)):
        if not fresh and (hit := _load(key)):
            results[i] = _from_cache(hit, state, qs)
            if on_done:
                on_done(results[i])
        else:
            todo.append(i)
    if not todo:
        return results  # type: ignore[return-value]

    require_key()
    kwargs = {"model": model} if model else {}
    gate = asyncio.Semaphore(CONCURRENCY)

    failures: dict[int, str] = {}

    async def one(client, i: int) -> None:
        state, qs = requests[i]
        async with gate:
            started = time.perf_counter()
            defanged = 0
            try:
                while True:
                    try:
                        sent = defang(state, defanged) if defanged else state
                        response = await client.system_one(sent, dict(qs), **kwargs)
                        break
                    except TypeSafeAPIError as error:
                        if not _refused(error) or defanged == 2:
                            raise
                        defanged += 1
            except (TypeSafeAPIError, TypeSafeError) as error:
                # One refused issue should not sink a scan of a hundred.
                failures[i] = str(_translate(error))
                return
        results[i] = _reading(response, started, state, shaped[i][1])
        results[i].defanged = defanged
        _save(keys[i], results[i].to_dict())
        if on_done:
            on_done(results[i])

    try:
        async with AsyncTypeSafeClient(retry=RETRY) as client:
            await asyncio.gather(*(one(client, i) for i in todo))
    except (TypeSafeAPIError, TypeSafeError) as error:
        raise _translate(error) from error
    if failures and len(failures) == len(todo) and len(todo) == len(requests):
        raise TriageError(next(iter(failures.values())))
    return results  # type: ignore[return-value]


def ask_many(requests, *, model: str | None = None, fresh: bool = False, on_done=None):
    """`ask_many_async` for callers that are not already in an event loop."""
    return asyncio.run(ask_many_async(requests, model=model, fresh=fresh, on_done=on_done))

"""The one place that talks to Laya.

Laya runs in this process: the checkpoint is downloaded from Hugging Face once,
loaded once, and every question after that is a local forward pass. Nothing
leaves the machine and there is no key.
"""

from __future__ import annotations

import os
import threading

# transformers probes for TensorFlow at import, and its runtime can deadlock
# model construction when it is installed. Laya's own advice: switch it off.
os.environ.setdefault("USE_TF", "0")

from tetris_duel.engine import EngineError  # noqa: E402

MODEL_ENV = "LAYA_MODEL"
DEVICE_ENV = "LAYA_DEVICE"
DEFAULT_MODEL = "convaiinnovations/laya-multilingual"

_agents: dict[str, object] = {}
_lock = threading.Lock()


def model_id(model: str | None = None) -> str:
    return model or os.environ.get(MODEL_ENV) or DEFAULT_MODEL


def agent(model: str | None = None):
    """The loaded checkpoint, loading it on first use.

    One model answers every request, and torch is not happy being driven from
    several threads at once, so the lock covers the forward pass as well.
    """
    key = model_id(model)
    with _lock:
        if key not in _agents:
            try:
                import laya

                _agents[key] = laya.load(key, device=os.environ.get(DEVICE_ENV) or None)
            except Exception as error:  # a missing checkpoint, no network, no disk
                raise EngineError(f"Could not load {key}: {error}") from error
        return _agents[key]


def ask(state: dict, questions: dict, model: str | None = None) -> dict:
    """Every question in one forward pass, answered against the same state."""
    loaded = agent(model)
    try:
        with _lock:
            return loaded.system_one(state, questions)
    except ValueError as error:  # Laya names the question it could not fit
        raise EngineError(f"Laya could not take the docket: {error}") from error


def count_tokens(text: str, model: str | None = None) -> int:
    """How much of Laya's fixed option budget a piece of text would use."""
    return len(agent(model).tok(" " + text, add_special_tokens=False)["input_ids"])


def head_budget(model: str | None = None) -> int:
    """Tokens a question and all of its options share, per the checkpoint's config."""
    return int(agent(model).cfg.get("head_max_len", 192))

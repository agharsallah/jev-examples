"""Fixtures recorded from a real run against omnigent-ai/omnigent.

The tests never touch the network: Jev's answers and GitHub's data are loaded
from these files, and everything under test is the plain code around them.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from triage.github import Label, Repo
from triage.taxonomy import Taxonomy

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def repo() -> Repo:
    raw = _load("omnigent-repo.json")
    raw["labels"] = [Label(**label) for label in raw["labels"]]
    return Repo(**raw)


@pytest.fixture
def tax() -> Taxonomy:
    return Taxonomy.from_dict(_load("omnigent-taxonomy.json"))


@pytest.fixture
def measurement() -> dict:
    """Issue #8107: a well-written bug with three 'may be related' neighbours."""
    m = _load("omnigent-8107.json")
    for answer in m["answers"].values():
        if answer["type"] == "score":
            answer["probabilities"] = {int(k): v for k, v in answer["probabilities"].items()}
    return copy.deepcopy(m)

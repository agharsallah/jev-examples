"""What the browser sends: request bodies, validated by FastAPI."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReadRequest(BaseModel):
    draft: str = Field(min_length=1, max_length=8000)
    to: str | None = Field(default=None, max_length=200)
    goal: str | None = Field(default=None, max_length=400)
    channel: str | None = Field(default=None, max_length=40)
    audience: str | None = None
    model: str | None = None
    deep: bool = True


class RailIn(BaseModel):
    """One measured dimension, as it came back from a previous read."""

    key: str
    score: float
    confidence: float
    level: str
    counted: bool


class FindingIn(BaseModel):
    key: str
    severity: str
    title: str
    fix: str
    value: float
    strength: float


class Measurement(BaseModel):
    """Everything Jev said about a draft, with none of the interpretation.

    The browser hands this back when the reader changes. Nothing in it depends
    on who the draft is for, which is exactly why it does not need asking again.
    """

    draft: str
    intent: str
    intent_confidence: float
    intent_ranked: list[tuple[str, float]]
    risk: str
    risk_confidence: float
    rails: list[RailIn]
    findings: list[FindingIn]


class RescoreRequest(BaseModel):
    measurement: Measurement
    audience: str

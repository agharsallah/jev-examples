"""Turning a GitHub issue into state Jev can read, and units it can point at.

Two jobs, both plain code. Cleaning keeps the state about the problem: template
comments, pasted megabyte logs and bot replies are distractors, and Jev's
accuracy falls as unrelated text grows. Splitting cuts the cleaned body into
units — sentences, list items, whole code blocks — each with the character
span it came from, so the UI can paint a judgment back onto the exact text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .github import Issue

# Characters, not tokens: ~4 chars a token keeps the body near 3k tokens,
# far inside the 32k state budget with room for comments and candidates.
BODY_BUDGET = 12_000
COMMENT_BUDGET = 1_500
MAX_COMMENTS = 8

# Code blocks longer than this are shown as head + tail. A stack trace's first
# and last lines carry the exception and the frame; the middle rarely matters.
CODE_HEAD, CODE_TAIL = 8, 4

# How many units get their own evidence questions. Beyond this the request
# grows without the highlights getting any more useful.
MAX_UNITS = 40

ABBREVIATIONS = {
    "mr",
    "mrs",
    "ms",
    "dr",
    "prof",
    "vs",
    "etc",
    "eg",
    "ie",
    "e.g",
    "i.e",
    "approx",
    "fig",
    "no",
    "vol",
    "inc",
    "ltd",
    "co",
    "v",
}

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_FENCE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.DOTALL | re.MULTILINE)
_DETAILS_TAGS = re.compile(r"</?(details|summary)[^>]*>", re.IGNORECASE)
_BLANKS = re.compile(r"\n{3,}")
_SENTENCE_END = re.compile(r"(?<=[.!?])[\"')\]]*\s+(?=[A-Z0-9`\"'(\[])")
_TRAILING_WORD = re.compile(r"([A-Za-z.]+)\.[\"')\]]*$")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
_EMPTY_CHECKBOX = re.compile(r"^\s*[-*]\s+\[ \]\s")
_NO_RESPONSE = re.compile(r"^_?no response_?$", re.IGNORECASE)


@dataclass
class Unit:
    """One piece of the body Jev can be asked about, and where it sits."""

    index: int
    text: str
    start: int
    end: int
    kind: str  # "sentence", "item", "code", "heading"

    @property
    def asked(self) -> bool:
        """Headings organise the text; they are shown but never judged."""
        return self.kind != "heading"


def _shorten_code(block: str) -> str:
    lines = block.split("\n")
    # Keep the fences; shorten what is between them.
    inner = lines[1:-1]
    if len(inner) <= CODE_HEAD + CODE_TAIL + 2:
        return block
    kept = inner[:CODE_HEAD] + [f"… {len(inner) - CODE_HEAD - CODE_TAIL} lines omitted …"]
    return "\n".join([lines[0], *kept, *inner[-CODE_TAIL:], lines[-1]])


def clean_text(text: str, budget: int = BODY_BUDGET) -> str:
    """Strip what is not the reporter talking, then cap the length."""
    text = text.replace("\r\n", "\n")
    text = _HTML_COMMENT.sub("", text)
    text = _DETAILS_TAGS.sub("", text)
    text = _FENCE.sub(lambda m: _shorten_code(m.group(0)), text)
    lines = [
        line
        for line in text.split("\n")
        if not _NO_RESPONSE.match(line.strip()) and not _EMPTY_CHECKBOX.match(line)
    ]
    text = _BLANKS.sub("\n\n", "\n".join(lines)).strip()
    if len(text) > budget:
        text = text[:budget].rsplit("\n", 1)[0] + "\n… (truncated)"
    return text


def _ends_on_abbreviation(candidate: str) -> bool:
    word = _TRAILING_WORD.search(candidate)
    return bool(word) and word.group(1).casefold() in ABBREVIATIONS


def _split_prose(text: str, offset: int, units: list[Unit]) -> None:
    """Sentences inside one paragraph or list item."""
    start = 0
    for match in _SENTENCE_END.finditer(text):
        if _ends_on_abbreviation(text[: match.start()]):
            continue
        _add(units, text[start : match.start()], offset + start, "sentence")
        start = match.end()
    _add(units, text[start:], offset + start, "sentence")


def _add(units: list[Unit], raw: str, start: int, kind: str) -> None:
    text = raw.strip()
    if not text:
        return
    lead = len(raw) - len(raw.lstrip())
    units.append(Unit(len(units), text, start + lead, start + lead + len(text), kind))


def split(body: str) -> list[Unit]:
    """Cut a cleaned body into units with character spans into that body."""
    units: list[Unit] = []
    cursor = 0
    for fence in _FENCE.finditer(body):
        _split_lines(body[cursor : fence.start()], cursor, units)
        _add(units, fence.group(0), fence.start(), "code")
        cursor = fence.end()
    _split_lines(body[cursor:], cursor, units)
    return units


def _split_lines(text: str, offset: int, units: list[Unit]) -> None:
    position = 0
    for line in text.split("\n"):
        start = offset + position
        position += len(line) + 1
        if not line.strip():
            continue
        if _HEADING.match(line):
            _add(units, line, start, "heading")
        elif re.match(r"^\s*([-*+]|\d+[.)])\s", line):
            _add(units, line, start, "item")
        else:
            _split_prose(line, start, units)


def asked_units(units: list[Unit]) -> list[Unit]:
    """The units that get evidence questions, capped, in reading order."""
    return [u for u in units if u.asked][:MAX_UNITS]


def human_comments(issue: Issue) -> list[dict]:
    """The thread without bots, each comment marked by who is speaking."""
    maintainer = {"OWNER", "MEMBER", "COLLABORATOR"}
    thread = []
    for comment in issue.comments:
        if comment.is_bot:
            continue
        if comment.author == issue.author:
            role = "reporter"
        elif comment.association in maintainer:
            role = "maintainer"
        else:
            role = "other user"
        body = clean_text(comment.body, COMMENT_BUDGET)
        if body:
            thread.append({"from": role, "text": body})
    return thread[:MAX_COMMENTS]

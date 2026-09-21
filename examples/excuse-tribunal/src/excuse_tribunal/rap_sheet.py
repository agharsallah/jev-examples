"""A criminal record, kept in the user's home directory.

Every hearing is appended, so the tribunal can tell repeat offenders what kind
of liar they have become over time.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

RAP_SHEET = Path.home() / ".excuse-tribunal" / "rap-sheet.jsonl"


@dataclass
class Record:
    when: str
    kind: str
    excuse: str
    ruling: str
    archetype: str
    believability: float


def _line(record: Record) -> str:
    return json.dumps(record.__dict__, ensure_ascii=False)


def record(kind: str, excuse: str, verdict, path: Path = RAP_SHEET) -> None:
    entry = Record(
        when=datetime.now(UTC).isoformat(timespec="seconds"),
        kind=kind,
        excuse=excuse.strip()[:280],
        ruling=verdict.ruling,
        archetype=verdict.archetype,
        believability=round(verdict.believability, 2),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_line(entry) + "\n")


def history(path: Path = RAP_SHEET) -> list[Record]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(Record(**json.loads(line)))
        except (json.JSONDecodeError, TypeError):
            continue  # A corrupted line is not worth a crash.
    return records


def summary(records: list[Record]) -> dict:
    if not records:
        return {}
    archetypes = Counter(r.archetype for r in records)
    rulings = Counter(r.ruling for r in records)
    return {
        "hearings": len(records),
        "average_believability": sum(r.believability for r in records) / len(records),
        "signature_move": archetypes.most_common(1)[0],
        "archetypes": archetypes,
        "rulings": rulings,
    }

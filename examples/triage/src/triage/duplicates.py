"""Finding issues that might be the same one, so Jev can judge them.

Recall is code's job: a BM25 ranking over the recent issues already fetched,
plus GitHub search with the issue's most distinctive words to reach older
history. Jev only sees the short list, and answers two questions about each
candidate — same problem, or merely related — because the difference is
exactly what an automated "may be related" comment gets wrong.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from . import github
from .clean import clean_text
from .github import Issue
from .jev import TriageError

SHORTLIST = 6
CANDIDATE_BODY = 900

_WORD = re.compile(r"[a-z][a-z0-9_.-]{2,}")
_STOP = set(
    """the and for that this with from have when what which there their they them then than
    into onto also just like only some such more most very will would should could can not
    does did doing done been being were was are has had how why who you your our its it's
    issue bug feature request error works working work using use used get got make made
    after before while where here want need needs expected actual behavior behaviour steps
    reproduce version still again able same other any all but out see seems""".split()
)


def words(text: str) -> list[str]:
    return [w.strip(".-_") for w in _WORD.findall(text.lower()) if w not in _STOP]


class BM25:
    """Okapi BM25 over title + body. Small, and good enough for recall."""

    def __init__(self, issues: list[Issue], k1: float = 1.4, b: float = 0.75) -> None:
        self.issues = issues
        self.docs = [Counter(words((i.title + " ") * 3 + i.body[:4000])) for i in issues]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg = (sum(self.lengths) / len(self.lengths)) if self.lengths else 1.0
        df = Counter(w for d in self.docs for w in d)
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}
        self.k1, self.b = k1, b

    def rank(self, query: list[str], exclude: int, top: int) -> list[tuple[Issue, float]]:
        scored = []
        for issue, doc, length in zip(self.issues, self.docs, self.lengths, strict=True):
            if issue.number == exclude:
                continue
            score = 0.0
            for w in set(query):
                if f := doc.get(w):
                    norm = (
                        f
                        * (self.k1 + 1)
                        / (f + self.k1 * (1 - self.b + self.b * length / self.avg))
                    )
                    score += self.idf.get(w, 0.0) * norm
            if score > 0:
                scored.append((issue, score))
        return sorted(scored, key=lambda s: -s[1])[:top]

    def distinctive(self, issue: Issue, count: int = 5) -> list[str]:
        """The title words that are rarest in the repo: the best search terms."""
        title = list(dict.fromkeys(words(issue.title)))
        return sorted(title, key=lambda w: -self.idf.get(w, 10.0))[:count]


_INDEXES: dict[int, tuple[list[Issue], BM25]] = {}


def index_for(corpus: list[Issue]) -> BM25:
    """One index per corpus list: a scan shortlists hundreds of issues against the same one."""
    hit = _INDEXES.get(id(corpus))
    if hit and hit[0] is corpus:
        return hit[1]
    if len(_INDEXES) > 8:
        _INDEXES.clear()
    index = BM25(corpus)
    _INDEXES[id(corpus)] = (corpus, index)
    return index


def shortlist(repo: str, issue: Issue, corpus: list[Issue], *, search: bool = True) -> list[Issue]:
    """Up to SHORTLIST candidates, best first, never the issue itself."""
    index = index_for(corpus)
    query = words(issue.title) * 2 + words(issue.body[:3000])
    ranked = {i.number: (i, s) for i, s in index.rank(query, issue.number, SHORTLIST * 2)}
    if search:
        try:
            found = github.search(repo, index.distinctive(issue))
        except TriageError:
            found = []  # Search is a bonus; the local ranking still stands.
        if found:
            rescored = BM25(found + [i for i, _ in ranked.values()])
            for candidate, score in rescored.rank(query, issue.number, SHORTLIST * 2):
                if candidate.number not in ranked or ranked[candidate.number][1] < score:
                    ranked[candidate.number] = (candidate, score)
    best = sorted(ranked.values(), key=lambda s: -s[1])
    return [candidate for candidate, _ in best[:SHORTLIST]]


def as_state(candidate: Issue) -> dict:
    return {
        "number": candidate.number,
        "title": candidate.title,
        "state": candidate.state.lower(),
        "body": clean_text(candidate.body, CANDIDATE_BODY),
    }

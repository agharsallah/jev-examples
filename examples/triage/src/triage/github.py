"""Reading a repository's labels and issues from GitHub. Read-only, always.

Everything goes through the GraphQL API because one query can carry an issue,
its labels and its comment thread, and a label's usage counts come back with
the label. Results are cached on disk and never expire on their own: GitHub is
asked again only when the caller passes `refresh` (the Refresh button, or
`--refresh`). That also keeps Jev quiet — an unchanged issue is an unchanged
state, and Jev's answers for it come from its own cache.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

from .jev import HOME, TriageError

API = "https://api.github.com/graphql"
CACHE = HOME / "github"

NO_TOKEN = (
    "No GitHub token, and unauthenticated GitHub is limited to 60 requests an hour.\n"
    "  export GITHUB_TOKEN=...   (a fine-grained token with public read access is enough)\n"
    "  or sign in once with      gh auth login"
)

_REPO = re.compile(
    r"^(?:https?://github\.com/)?(?P<owner>[\w.-]+)/(?P<name>[\w.-]+?)(?:\.git)?"
    r"(?:(?:/issues/|#)(?P<number>\d+))?/?$"
)


@dataclass
class Label:
    name: str
    description: str = ""
    color: str = ""
    issues: int = 0
    pull_requests: int = 0


@dataclass
class Comment:
    author: str
    association: str
    body: str
    created_at: str
    is_bot: bool = False


@dataclass
class Issue:
    number: int
    title: str
    body: str
    state: str
    url: str
    author: str
    association: str
    created_at: str
    updated_at: str | None = None
    closed_at: str | None = None
    state_reason: str | None = None
    labels: list[str] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
    comment_count: int = 0

    @classmethod
    def from_dict(cls, raw: dict) -> Issue:
        raw = dict(raw)
        raw["comments"] = [Comment(**c) for c in raw.get("comments", [])]
        return cls(**raw)


@dataclass
class Repo:
    owner: str
    name: str
    description: str = ""
    url: str = ""
    open_issues: int = 0
    labels: list[Label] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"


def parse(ref: str) -> tuple[str, str, int | None]:
    """`owner/repo`, `owner/repo#12`, or a github.com URL to either."""
    match = _REPO.match(ref.strip())
    if not match:
        raise TriageError(
            f"Not a GitHub repo I can read: {ref!r}. Try owner/repo or owner/repo#123."
        )
    number = match.group("number")
    return match.group("owner"), match.group("name"), int(number) if number else None


def token() -> str:
    """GITHUB_TOKEN if set, otherwise whatever `gh` is signed in with."""
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        if value := os.environ.get(name, "").strip():
            return value
    if shutil.which("gh"):
        done = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if done.returncode == 0 and done.stdout.strip():
            return done.stdout.strip()
    raise TriageError(NO_TOKEN)


def _query(query: str, variables: dict, *, attempts: int = 4) -> dict:
    """One GraphQL call. GitHub's 502s on heavy queries are transient; retry them."""
    for attempt in range(attempts):
        try:
            response = httpx.post(
                API,
                json={"query": query, "variables": variables},
                headers={"Authorization": f"Bearer {token()}", "User-Agent": "jev-triage"},
                timeout=60,
            )
        except httpx.HTTPError as error:
            if attempt + 1 < attempts:
                time.sleep(1.5 * 2**attempt)
                continue
            raise TriageError(f"Could not reach GitHub: {error}") from error
        if response.status_code >= 500 and attempt + 1 < attempts:
            time.sleep(1.5 * 2**attempt)
            continue
        break
    if response.status_code == 401:
        raise TriageError("GitHub refused the token (HTTP 401).")
    if response.status_code >= 400:
        raise TriageError(f"GitHub answered HTTP {response.status_code}.")
    payload = response.json()
    if errors := payload.get("errors"):
        raise TriageError("GitHub: " + "; ".join(e.get("message", "?") for e in errors))
    return payload["data"]


# -- caching -----------------------------------------------------------------


def _cache_path(owner: str, name: str, what: str) -> Path:
    return CACHE / f"{owner}__{name}".lower() / f"{what}.json"


def _cached(path: Path, refresh: bool):
    if refresh:
        return None
    try:
        blob = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return blob["data"]


def _store(path: Path, data) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"fetched_at": time.time(), "data": data}))
    except OSError:
        pass


# -- queries -----------------------------------------------------------------

_ISSUE_FIELDS = """
  number title body state url createdAt updatedAt closedAt stateReason
  author { __typename login } authorAssociation
  labels(first: 40) { nodes { name } }
  comments(first: 25) {
    totalCount
    nodes { author { __typename login } authorAssociation body createdAt }
  }
"""

_REPO_QUERY = """
query($owner: String!, $name: String!, $after: String, $first: Int!) {
  repository(owner: $owner, name: $name) {
    description url
    issues(states: OPEN) { totalCount }
    labels(first: $first, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { name description color issues { totalCount } pullRequests { totalCount } }
    }
  }
}
"""

_ISSUES_QUERY = f"""
query($owner: String!, $name: String!, $first: Int!, $after: String, $states: [IssueState!]) {{
  repository(owner: $owner, name: $name) {{
    issues(first: $first, after: $after, states: $states,
           orderBy: {{field: CREATED_AT, direction: DESC}}) {{
      pageInfo {{ hasNextPage endCursor }}
      nodes {{ {_ISSUE_FIELDS} }}
    }}
  }}
}}
"""

_ISSUE_QUERY = f"""
query($owner: String!, $name: String!, $number: Int!) {{
  repository(owner: $owner, name: $name) {{
    issue(number: $number) {{ {_ISSUE_FIELDS} }}
  }}
}}
"""

_SEARCH_QUERY = f"""
query($q: String!, $first: Int!) {{
  search(query: $q, type: ISSUE, first: $first) {{
    nodes {{ ... on Issue {{ {_ISSUE_FIELDS} }} }}
  }}
}}
"""

# Accounts that post on issues without being a person: triage bots, CI, and
# the duplicate checkers whose guesses would otherwise leak into the state.
_BOT_LOGINS = {"github-actions", "dependabot", "renovate", "stale", "codecov", "netlify"}


def _is_bot(author: dict | None) -> bool:
    if not author:
        return True  # A deleted account ("ghost") has nothing to tell us.
    login = author.get("login", "")
    return (
        author.get("__typename") == "Bot"
        or login.endswith("[bot]")
        or login.casefold() in _BOT_LOGINS
    )


def _issue(node: dict) -> Issue:
    author = node.get("author") or {}
    comments = node.get("comments") or {}
    return Issue(
        number=node["number"],
        title=node["title"],
        body=node.get("body") or "",
        state=node["state"],
        url=node["url"],
        author=author.get("login", "ghost"),
        association=node.get("authorAssociation", "NONE"),
        created_at=node["createdAt"],
        updated_at=node.get("updatedAt"),
        closed_at=node.get("closedAt"),
        state_reason=node.get("stateReason"),
        labels=[label["name"] for label in (node.get("labels") or {}).get("nodes", [])],
        comments=[
            Comment(
                author=(c.get("author") or {}).get("login", "ghost"),
                association=c.get("authorAssociation", "NONE"),
                body=c.get("body") or "",
                created_at=c["createdAt"],
                is_bot=_is_bot(c.get("author")),
            )
            for c in comments.get("nodes", [])
        ],
        comment_count=comments.get("totalCount", 0),
    )


def repo(ref: str, *, refresh: bool = False) -> Repo:
    """The repository and every label it has, with how often each is used."""
    owner, name, _ = parse(ref)
    path = _cache_path(owner, name, "repo")
    if (hit := _cached(path, refresh)) is not None:
        hit["labels"] = [Label(**label) for label in hit["labels"]]
        return Repo(**hit)

    labels: list[Label] = []
    after = None
    while True:
        # Counting each label's uses is expensive on big repos; small pages
        # keep GitHub from timing the query out.
        data = _query(_REPO_QUERY, {"owner": owner, "name": name, "after": after, "first": 25})
        found = data.get("repository")
        if found is None:
            raise TriageError(f"GitHub has no repository {owner}/{name} (or it is private).")
        page = found["labels"]
        labels += [
            Label(
                name=node["name"],
                description=(node.get("description") or "").strip(),
                color=node.get("color") or "",
                issues=node["issues"]["totalCount"],
                pull_requests=node["pullRequests"]["totalCount"],
            )
            for node in page["nodes"]
        ]
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]

    result = Repo(
        owner=owner,
        name=name,
        description=found.get("description") or "",
        url=found.get("url") or f"https://github.com/{owner}/{name}",
        open_issues=found["issues"]["totalCount"],
        labels=labels,
    )
    _store(path, asdict(result))
    return result


def issues(ref: str, *, limit: int = 300, state: str = "all", refresh: bool = False) -> list[Issue]:
    """The most recent issues, newest first. `state` is open, closed or all."""
    owner, name, _ = parse(ref)
    path = _cache_path(owner, name, f"issues-{state}-{limit}")
    if (hit := _cached(path, refresh)) is not None:
        return [Issue.from_dict(raw) for raw in hit]

    states = {"open": ["OPEN"], "closed": ["CLOSED"]}.get(state, ["OPEN", "CLOSED"])
    found: list[Issue] = []
    after = None
    while len(found) < limit:
        data = _query(
            _ISSUES_QUERY,
            {
                "owner": owner,
                "name": name,
                "first": min(50, limit - len(found)),
                "after": after,
                "states": states,
            },
        )
        page = data["repository"]["issues"]
        found += [_issue(node) for node in page["nodes"]]
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    _store(path, [asdict(i) for i in found])
    return found


def issue(ref: str, number: int | None = None, *, refresh: bool = False) -> Issue:
    """One issue with its thread."""
    owner, name, parsed = parse(ref)
    number = number or parsed
    if number is None:
        raise TriageError("Which issue? Pass owner/repo#123.")
    path = _cache_path(owner, name, f"issue-{number}")
    if (hit := _cached(path, refresh)) is not None:
        return Issue.from_dict(hit)
    data = _query(_ISSUE_QUERY, {"owner": owner, "name": name, "number": number})
    node = (data.get("repository") or {}).get("issue")
    if node is None:
        raise TriageError(f"{owner}/{name}#{number} is not an issue (a pull request, or missing).")
    found = _issue(node)
    _store(path, asdict(found))
    return found


def search(ref: str, words: list[str], *, first: int = 20) -> list[Issue]:
    """Issues anywhere in the repo's history that share any of these words.

    The recent-issues sample only reaches back so far; duplicates are often
    old. GitHub's search does the recall, Jev does the judging.
    """
    owner, name, _ = parse(ref)
    if not words:
        return []
    terms = " OR ".join(words[:5])
    query = f"repo:{owner}/{name} is:issue {terms}"
    path = _cache_path(owner, name, "search-" + re.sub(r"\W+", "-", " ".join(words[:5]))[:80])
    if (hit := _cached(path, False)) is not None:
        return [Issue.from_dict(raw) for raw in hit]
    data = _query(_SEARCH_QUERY, {"q": query, "first": first})
    found = [_issue(node) for node in data["search"]["nodes"] if node]
    _store(path, [asdict(i) for i in found])
    return found

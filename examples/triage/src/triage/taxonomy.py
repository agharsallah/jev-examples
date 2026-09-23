"""Reading a repository's labels before reading any issue.

Every repo invents its own labels, so the triage questions cannot be written
in advance. This module works them out:

1. Code does what code can know exactly: which labels have never been put on
   an issue (PR-only, or dead), and which share a prefix like `comp:` or `P1-`.
2. Jev answers one Choice per remaining label: what *role* does it play —
   issue type, component, priority, workflow status…
3. Code turns roles and prefixes into families. A family of mutually exclusive
   labels (one type, one priority) becomes a Choice in every triage request;
   a standalone attribute like `good first issue` becomes a Noul; workflow and
   release labels are left alone, because nothing in an issue's text decides
   them.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field

from typesafe_sdk import Choice

from . import jev
from .github import Label, Repo

ROLES = {
    "issue_type": {
        "what": "Says what kind of report the issue is",
        "examples": ["bug", "feature request", "documentation", "question", "enhancement"],
    },
    "component": {
        "what": "Names the part of the project, module or area the issue is about",
        "examples": ["comp:server", "area/cli", "frontend", "windows", "docs site"],
    },
    "priority": {
        "what": "Ranks how urgently the issue should be worked on",
        "examples": ["P1", "priority: high", "urgent", "low priority"],
    },
    "severity": {
        "what": "Rates how bad the impact of the problem is",
        "examples": ["severity:critical", "S2", "major", "minor"],
    },
    "attribute": {
        "what": (
            "A property a reader can judge from the issue text itself, "
            "independent of the type or component"
        ),
        "examples": [
            "good first issue",
            "needs more info",
            "breaking change",
            "security",
            "regression",
        ],
    },
    "maintainer_decision": {
        "what": "Records a decision a maintainer made about the issue, not something in its text",
        "examples": ["wontfix", "invalid", "duplicate", "approved", "accepted"],
    },
    "workflow_status": {
        "what": "Tracks where the issue is in a process, or marks automation",
        "examples": ["triaged", "stale", "in progress", "waiting-on-author", "needs-triage"],
    },
    "release": {
        "what": "Ties the issue to a version, milestone or release train",
        "examples": ["0.3.0", "v2", "next-release", "backport"],
    },
    "other": {
        "what": "Fits none of the other roles",
        "examples": [],
    },
}

# Families whose labels exclude each other on one issue: one type, one priority.
EXCLUSIVE = {"issue_type", "priority", "severity"}
# Families that get a "primary" Choice: several may apply, one is the main one.
PRIMARY = {"component"}
# Roles that become one Noul per label.
PER_LABEL = {"attribute"}

FAMILY_TITLES = {
    "issue_type": "type",
    "component": "component",
    "priority": "priority",
    "severity": "severity",
}

# Priority-style tokens: P0, P1-high, S2, sev1. Grouped by their letter.
_RANKED = re.compile(r"^(p|s|sev|pri)[\s_-]?\d\b", re.IGNORECASE)
_PREFIX = re.compile(r"^([\w .-]{1,24}?)\s*[:/]\s*\S")


@dataclass
class Family:
    """A set of labels one question chooses between."""

    key: str
    role: str
    title: str
    labels: list[str]
    mode: str  # "choice" (exclusive or primary) or "nouls" (one per label)
    descriptions: dict[str, str] = field(default_factory=dict)
    # How often each label is used on issues, as a word: the base rate a new
    # maintainer would pick up in a week, which a label description never says.
    usage: dict[str, str] = field(default_factory=dict)


@dataclass
class Taxonomy:
    """How Jev read the labels, and the triage schema that falls out of it."""

    repo: str
    roles: dict[str, dict]  # label -> {role, confidence, probabilities, prefix}
    families: list[Family]
    ignored: dict[str, str]  # label -> why it gets no question
    reading: dict | None = None

    def family(self, role: str) -> Family | None:
        return next((f for f in self.families if f.role == role), None)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> Taxonomy:
        raw = dict(raw)
        raw["families"] = [Family(**f) for f in raw["families"]]
        return cls(**raw)


def prefix_of(name: str) -> str | None:
    """`comp:server` -> `comp`, `P1-high` -> `p`, `Bug` -> None."""
    if match := _RANKED.match(name):
        return match.group(1).casefold()
    if match := _PREFIX.match(name):
        return match.group(1).strip().casefold()
    return None


def usage_bucket(count: int) -> str:
    """Counts go to Jev as words. It judges meaning well and arithmetic badly."""
    if count == 0:
        return "never"
    if count < 5:
        return "rarely"
    if count < 50:
        return "sometimes"
    return "often"


def _label_state(repo: Repo, used: list[Label]) -> dict:
    return {
        "repository": {"name": repo.slug, "description": repo.description},
        "labels": [
            {
                "name": label.name,
                "description": label.description or None,
                "used_on_issues": usage_bucket(label.issues),
                "used_on_pull_requests": usage_bucket(label.pull_requests),
            }
            for label in used
        ],
    }


def role_questions(used: list[Label]) -> dict[str, Choice]:
    """One Choice per label: what role it plays in this repo's triage."""
    return {
        f"role__{i}": Choice(
            instructions={
                "label": {"name": label.name, "description": label.description or None},
                "question": (
                    "In this repository, what role does the issue label `label` play? "
                    "Judge from its name, its description, and the other labels in "
                    "`labels` it sits alongside."
                ),
            },
            criteria=ROLES,
        )
        for i, label in enumerate(used)
    }


def read_labels(repo: Repo, *, model: str | None = None, fresh: bool = False) -> Taxonomy:
    """One request: Jev reads every label that has ever been on an issue."""
    ignored: dict[str, str] = {}
    used: list[Label] = []
    for label in repo.labels:
        if label.issues == 0:
            ignored[label.name] = (
                "only on pull requests" if label.pull_requests else "never used on an issue"
            )
        else:
            used.append(label)

    roles: dict[str, dict] = {}
    reading = None
    if used:
        reading = jev.ask(_label_state(repo, used), role_questions(used), model=model, fresh=fresh)
        for i, label in enumerate(used):
            answer = reading.answers[f"role__{i}"]
            roles[label.name] = {
                "role": answer["choice"],
                "confidence": answer["confidence"],
                "probabilities": answer["probabilities"],
                "prefix": prefix_of(label.name),
                "issues": label.issues,
            }
    families = build_families(repo.labels, roles, ignored)
    return Taxonomy(
        repo=repo.slug,
        roles=roles,
        families=families,
        ignored=ignored,
        reading=reading.to_dict() | {"questions": reading.questions} if reading else None,
    )


def build_families(
    labels: list[Label], roles: dict[str, dict], ignored: dict[str, str]
) -> list[Family]:
    """Plain code from here on: roles and prefixes into question families.

    A prefix group takes the role most of its members got, so one stray
    reading (`comp:infra` read as a release label) cannot split `comp:*`.
    Unprefixed labels join the prefix group of their role when there is
    exactly one, else they form a family of their own.
    """
    descriptions = {label.name: label.description for label in labels}
    by_prefix: dict[str, list[str]] = defaultdict(list)
    for name, info in roles.items():
        if info["prefix"]:
            by_prefix[info["prefix"]].append(name)

    # Settle each prefix group's role by majority, weighted by use.
    group_role: dict[str, str] = {}
    for prefix, names in by_prefix.items():
        votes = Counter()
        for name in names:
            votes[roles[name]["role"]] += 1 + roles[name]["issues"]
        group_role[prefix] = votes.most_common(1)[0][0]

    members: dict[tuple[str, str], list[str]] = defaultdict(list)
    for name, info in roles.items():
        prefix = info["prefix"]
        if prefix and len(by_prefix[prefix]) > 1:
            role = group_role[prefix]
            members[(role, prefix)].append(name)
        else:
            role = info["role"]
            members[(role, "")].append(name)

    # Fold loose labels into their role's single prefix group, if there is one.
    for (role, prefix), names in list(members.items()):
        if prefix:
            continue
        groups = [key for key in members if key[0] == role and key[1]]
        if len(groups) == 1 and role in EXCLUSIVE | PRIMARY:
            members[groups[0]] += names
            del members[(role, prefix)]

    families: list[Family] = []
    for (role, prefix), names in sorted(members.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        names = sorted(names, key=lambda n: -roles[n]["issues"])
        if role in EXCLUSIVE | PRIMARY:
            if len(names) < 2:
                ignored.update({n: f"the only {role.replace('_', ' ')} label" for n in names})
                continue
            key = FAMILY_TITLES[role] + (f"_{_slug(prefix)}" if prefix else "")
            families.append(
                Family(
                    key=key,
                    role=role,
                    title=FAMILY_TITLES[role] + (f" ({prefix}…)" if prefix else ""),
                    labels=names,
                    mode="choice",
                    descriptions={n: descriptions.get(n, "") for n in names},
                    usage={n: usage_bucket(roles[n]["issues"]) for n in names},
                )
            )
        elif role in PER_LABEL:
            families.append(
                Family(
                    key="attribute" + (f"_{_slug(prefix)}" if prefix else ""),
                    role=role,
                    title="attributes" + (f" ({prefix}…)" if prefix else ""),
                    labels=names,
                    mode="nouls",
                    descriptions={n: descriptions.get(n, "") for n in names},
                    usage={n: usage_bucket(roles[n]["issues"]) for n in names},
                )
            )
        else:
            reason = {
                "maintainer_decision": "a maintainer's decision, not in the text",
                "workflow_status": "process or automation state",
                "release": "a release or version marker",
            }.get(role, "no clear role")
            ignored.update(dict.fromkeys(names, reason))

    # Several families may share a role (two component schemes); the busiest
    # one is the primary and keeps the short key the policy looks for.
    seen: set[str] = set()
    families.sort(key=lambda f: -sum(roles[n]["issues"] for n in f.labels))
    for family in families:
        if family.role in seen or family.mode != "choice":
            continue
        seen.add(family.role)
        family.key = FAMILY_TITLES[family.role]
        family.title = FAMILY_TITLES[family.role]
    return sorted(families, key=lambda f: list(ROLES).index(f.role))


def _slug(text: str) -> str:
    return re.sub(r"\W+", "_", text).strip("_")

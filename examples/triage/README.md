# Triage

Point it at any GitHub repo. [Jev](https://docs.typesafe.ai/models) reads the repo's labels,
then every issue, and returns numbers; plain Python decides which labels fit, whether it is a
duplicate, and who should look at it. Read-only — nothing is ever written to GitHub.

```
$ triage issue omnigent-ai/omnigent#8107 --no-trace

#8107 [Bug] opencode-native permission/question prompt visible only in terminal, chat shows
no approval card or notice (session looks stalled)
 Ready — labels can be applied
╭─ What Jev read ─────────────────────────────────────────────────────────────╮
│ kind           bug ████████████████████        1.00                         │
│                confidence 1.00                                              │
│ impact         ███████████·········          2.18/4                         │
│ clarity        ████████████████████          3.00/3                         │
│ actionability  ███████████████████·          2.89/3                         │
│ priority       ████████████········            0.61                         │
╰─────────────────────────────────────────────────────────────────────────────╯
suggested label            ┃ family              ┃    p ┃
Bug  (already on it)       │ type                │ 1.00 │ apply
comp:harnesses             │ component           │ 0.91 │ apply
P2-medium  (already on it) │ priority            │ 0.79 │ apply
severity:S1                │ severity            │ 0.49 │ unsure
help wanted                │ attributes          │ 0.67 │ confirm
label drift component: on it is comp:harness-t2 (p 0.05); Jev reads comp:harnesses (p 0.91)
Duplicate check
   # ┃ candidate                                        ┃ same problem ┃ related ┃
7212 │ [Bug] Claude-native terminal confirmations and…  │         0.16 │    0.87 │ related
8101 │ antigravity: 16 of 18 agy requestedInteraction…  │         0.13 │    0.82 │ related
7405 │ [Bug] claude-native: approval card stays stuck…  │         0.11 │    0.66 │ related
122 questions in one request · 44,555 tokens · $0.0019 · 1.10s · jev-1.13.0
```

*(A real run, trimmed. Yours will differ a little; Jev is a model, not a lookup table.)*

That duplicate check is the example in miniature. The repo's own bot commented "#1551,
#8101, #7212 may be related", and the reporter replied that none of them is the same
problem. Jev is asked both questions separately — *same underlying problem?* and *related
enough to look at?* — and keeps the distinction the reporter had to explain.

## Setup

From the repo root — the examples are a uv workspace, so one `uv sync` covers them all:

```bash
uv sync
cp .env.example .env          # then put your TYPESAFE_API_KEY in it
uv run triage issue omnigent-ai/omnigent#8107
uv run triage serve           # the whole thing, in a browser
```

GitHub is read through its GraphQL API, which needs a token: `GITHUB_TOKEN` if it is set,
otherwise whatever `gh auth login` signed you in with. A token with public read access is
enough. Everything fetched, and every Jev answer, is cached under `~/.triage/`
(`TRIAGE_HOME` moves it), and nothing is re-read on its own: GitHub is asked again only when
you refresh (the **Refresh from GitHub** button, *fresh* on an issue, or `--refresh`). Because
an unchanged issue is an unchanged request, Jev answers it from the cache too — a refresh only
pays for the issues that actually changed.

## Commands

| Command | What it does |
| --- | --- |
| `triage overview owner/repo` | Every open issue at once: ready, good first issues, waiting on a decision, duplicates |
| `triage taxonomy owner/repo` | How Jev read the repo's labels, and the questions that fall out of it |
| `triage issue owner/repo#123` | One issue: one request, every question, and the policy trace (`--raw` prints the exact request) |
| `triage scan owner/repo -n 100` | The most recent open issues, all at once, sorted into lanes |
| `triage eval owner/repo -n 150` | Agreement with the labels already on issues, and calibration |
| `triage serve` | The browser: overview, issue page, queue, evaluation |

## Two requests, not one

Every repo invents its own labels, so the triage questions can't be written in advance.

**First, the labels** (`taxonomy.py`, once per repo). Code does what code can know exactly:
labels never put on an issue are PR-only or dead, and labels sharing a prefix (`comp:`,
`P1-`, `area/`) are probably one family. Then one request asks Jev, per label, *what role
does this label play here?* — issue type, component, priority, severity, an attribute you can
judge from the text, a maintainer's decision, workflow state, a release marker. Code turns the
answers into families: exclusive ones (one type, one priority) become a Choice in every
triage; attributes like `good first issue` become a Noul each; workflow and release labels get
no question, because nothing in an issue's text decides them.

On omnigent that is 54 labels in 0.75 seconds for $0.0015, and it comes out as `type`,
sixteen `comp:*` labels, `P0–P3` and `severity:*`, with `size/*`, `triaged` and the six
`validated:*` states left alone. The same code reads astral-sh/uv's `area:*` scheme and
pallets/click's component-only labels without changing a line.

**Then, each issue** (`questions.py`, one request per issue, ~120 questions):

| Question | Primitive | Why it is asked |
| --- | --- | --- |
| kind of report | Choice | bug / feature / docs / question / chore, independent of the repo's labels |
| each label family | Choice | the repo's own labels, in the repo's own words, plus `none_fit` |
| each attribute label | Noul | several may apply; each is absolute, not relative |
| impact, clarity, actionability, scope, newcomer-friendliness, frustration | Score | each on its own rubric; priority, readiness and beginner scores are weighted blends in code |
| needs a maintainer or product decision | Noul | "ready" means decided, not just well written |
| repro steps, expected vs actual, version, error output… | Noul | the checklist a maintainer runs in their head |
| security-sensitive, spam, *tries to steer triage* | Noul | issue text is data, and some of it argues for its own label |
| answered / fixed / waiting on the reporter | Noul | read from the human comments only |
| same problem as candidate *i*, related to it | Noul × 2 | candidates found by code: BM25 over recent issues plus GitHub search |
| what each sentence signals | Choice per unit | the highlights, and what the counterfactuals test |

All of it is speculative fan-out: repro questions are asked of feature requests too, and the
policy ignores them there. They cost almost nothing in the same request; a second request
would cost a round trip.

Two things are deliberately **not** in the state: the labels already on the issue, and every
bot comment. Both would hand Jev the answer it is meant to give (omnigent's triage bot posts
its priority as a comment).

## The whole backlog

Open a repo in `triage serve` and it starts on the **Overview**: every open issue, read
once, laid out for the person planning the week rather than the person triaging one issue.

- **Tiles** that count, and filter to: ready to pick up, good first issues, waiting on a
  decision, ask the reporter, in a duplicate cluster, handle privately, close candidates,
  label drift.
- **The map** — every issue as a dot, readiness across, impact up, coloured by kind. The
  quadrants are *do next* (important and ready), *unblock first* (important, not ready),
  *quick wins* and *backlog*; click one to filter.
- **Where the work is** — Jev's component pick × kind, as stacked bars; a segment filters to
  that component and kind.
- **Shortlists** — the top of each list, with the number it was ranked by and why.
- **Duplicate clusters** — union-find over the pairwise *same problem* answers, drawn as a
  small graph, with the oldest issue marked as the one to keep and a note when one member
  is already closed ("check whether the open one is fixed too").
- **Every issue** — a sortable table with the scores and flags; any row, dot or list item
  opens the full triage, and *back to the overview* keeps the filters.

The last overview of each repo is saved, and opening the page shows it straight away — the
page reads that file and asks neither GitHub nor Jev anything until you press **Refresh from
GitHub**. Every filter narrows every view at once, and the three knobs — the readiness bar, the
beginner bar, the duplicate threshold — recompute everything in the browser. The page prints
the weights next to the scores: readiness is 40% actionability, 25% clarity, 20% *decided*
(1 − needs a decision), 10% reproducible (bugs only), 5% focused; the beginner score is 55%
newcomer-friendliness, 25% small scope, 20% clarity.

The overview leaves out the per-sentence evidence questions — it never draws highlights, and
they are most of a request — so an issue costs about **$0.0003** there instead of $0.002. On
omnigent: all 543 open issues, 23,892 questions, **$0.157, 26 seconds** the first time (eight
requests in flight) and free after that. It found 172 issues ready to pick up, 49 good first
issues and 12 duplicate clusters, among them #7018 and #7014 (p 0.98, the same report twice)
and #7766, which explains #3095 "Can't uninstall" (p 0.96). The issue page asks the full set of
questions, so its numbers can differ a little from the overview's.

## How it shows its working

Jev does not write explanations. Everything the UI calls "why" is measured:

- **Distributions, not just picks.** Every Choice comes back with a probability on every
  option; the bars are that distribution.
- **Sentence evidence.** Each sentence, list item or code block gets its own Choice — *what
  kind of report does this part, on its own, signal?* — with the whole issue still in the
  state. That's the highlighting on the issue page, and clicking a unit shows its numbers.
- **Counterfactuals.** Take the strongest evidence out, ask the decision questions again, and
  report how far each call moved. On #8107 nothing moves more than 0.07 — "robust: no single
  part carries the call" — which is a finding, not a failure. On #7820, taking out the title
  (and its `[Bug]` prefix) drops *bug* from 0.92 to 0.71, while no single sentence of the body
  moves it more than 0.03: the title is carrying a fifth of that call.
- **The policy trace.** Every rule in `policy.py`, the number it read, the bar it compared
  against, and whether it fired.
- **The raw request.** The exact state and questions sent, and the answers that came back.

## The code owns the verdict

`policy.py` is plain Python over the answers: label a family when its Choice confidence
clears a bar, suggest it for confirmation above a floor, route security to a private lane,
steering attempts and an unsure *kind* to a human, a bug missing two essentials to *ask the
reporter* (with a reply assembled from fixed lines — selected, never generated). Every
threshold is a named setting.

In the browser those settings are sliders. Moving one sends the same answers back to be
rescored — the verdict changes, the answers do not, and Jev is not asked again. That works for
a whole queue too.

## Does it agree with the people who labelled these issues?

`triage eval` uses the dataset GitHub hands over for free: recent issues that already carry a
type, component or priority label. They are triaged with those labels hidden, and each family
Choice is compared to what's on the issue. On omnigent, 100 issues, $0.096:

| family | agree | top-2 | calibration error | at ≥ 0.9 confidence |
| --- | --- | --- | --- | --- |
| type | 94% | 100% | 0.03 | 85% of issues auto-labelled, 100% of those agree |
| priority | 74% | 95% | 0.07 | 13% auto-labelled, 92% agree |
| component | 58% | 85% | 0.24 | 41% auto-labelled, 88% agree |

The calibration chart is the headline: for *type*, when Jev says 0.8 it is right about 80% of
the time, which is what makes an auto-apply threshold mean something. The coverage curve is
the knob a maintainer actually sets: raise the bar, fewer issues clear it, more of those
agree.

*Component* is the interesting failure, and the page names it: 47% of the misses are one
pair — the issue carries `comp:harness-t1`, Jev reads `comp:harnesses`. Their descriptions are
"Highest-usage harnesses" and "SDK harnesses (Claude, Cursor, etc.)"; nothing says which
harness is in which tier. That is missing evidence, not a model error: no reader of the issue
text could make that call. When one confusion dominates, the fix is in the label
descriptions — and the eval is how you find out.

It says "agreement", not "accuracy", on purpose. The labels on omnigent's issues were applied
by another (LLM) bot; a disagreement is as likely to be a mislabelled issue as a Jev mistake.
The "disagrees most confidently" list is where to look for both.

## One thing that surprised us

Some issues are refused with HTTP 403 before they reach the model: a firewall in front of the
API scores the whole request, and an issue full of pasted shell one-liners
(`curl … && tar …`) adds up. `jev.py` retries once with backticks as plain quotes, then with
code and links replaced by placeholders, and the reading records which it took (1 of 100
omnigent issues needed it, and it needed the second step). A scan never fails on one issue; a refused issue is
listed as skipped.

## Layout

```
src/triage/
  github.py      GraphQL reads + disk cache (labels with usage counts, issues, search)
  clean.py       strip templates/bots, shorten logs, split into units with spans
  taxonomy.py    label roles → question families
  questions.py   everything the triage request asks
  jev.py         the only module that calls the API; response cache; firewall fallback
  duplicates.py  BM25 recall + GitHub search; Jev judges the shortlist
  policy.py      the verdict, with a trace — no network
  explain.py     counterfactual re-asks
  triage.py      one issue, start to finish
  scan.py        many issues at once; stateless queue rescoring
  overview.py    the whole backlog: composites, ages, duplicate edges, breakdowns
  evaluate.py    agreement, calibration, coverage, confusions
  render.py      terminal output
  web.py         FastAPI over the same functions
web/src/         TypeScript for the browser (compiled into static/js)
tests/           no network: recorded omnigent fixtures + hand-built answers
```

`uv run --group dev pytest` from this directory runs the tests without a key.

# Outbox

A second opinion on anything you are about to send. [Jev](https://docs.typesafe.ai/models)
reads the draft and returns numbers; plain Python decides whether to send it.

```
$ outbox check "just circling back on the migration doc -- no rush at all!! sorry to be a pain" --to "my manager"

OUTBOX · a second opinion before you hit send

╭──────────────────────────────────────────────────────────────────────────────╮
│                                                                              │
│   REWRITE IT   28/100 for a manager                                          │
│  The draft is working against you. Start from what you actually want.        │
│                                                                              │
│  reads as a request (96% confident) · ignored (92%)                          │
│  fit for a manager: 78/100 · a manager wants the point first, the ask        │
│  second, and no archaeology                                                  │
│                                                                              │
│        clarity ·················◆·─────── 2.78 too low for a manager         │
│  actionability ·······◆···········─────── 1.16 too low for a manager         │
│     directness ········◆·········──────── 1.31 too low for a manager         │
│         warmth ············───────◆───··· 3.07 on target                     │
│      formality ····◆····───────────······ 0.61 too low for a manager         │
│        brevity ············─◆─────────··· 2.05 on target                     │
│                                                                              │
│  !  The point is buried under hedging                                   93%  │
│     Cut 'just', 'maybe', 'I might be wrong' and 'no rush'. The point         │
│     survives them.                                                           │
│  !  The reader is missing context they need                             88%  │
│     One line saying what this is about saves the round trip asking.          │
│  !  Nothing is actually asked                                           88%  │
│     Write the ask as a sentence starting with a verb, and put it near        │
│     the top.                                                                 │
│  !  There are more apologies than the situation earns                   75%  │
│     Keep the first one. Delete the rest.                                     │
│  ·  No timing is given                                                  95%  │
│     'By Thursday' turns a request into something the reader can              │
│     schedule.                                                                │
│                                                                              │
│  just circling back on the migration doc -- no rush at all!! sorry to be a   │
│  pain                                                                        │
│                                                                              │
│  ▌ hedging   ▌ could go                                                      │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
 33 questions in 2 requests · 2754 in / 755 out
```

*(A real run. Yours will differ a little; Jev is a model, not a lookup table.)*

The `◆` is where the draft landed on that dimension. The `─────` is the stretch
a manager wants it in. Everything the desk says is the distance between those
two, and both halves are legible: Jev supplied the position, `audience.py`
supplied the target.

## Setup

From the repo root — the examples are a uv workspace, so one `uv sync` covers
them all:

```bash
uv sync
cp .env.example .env          # then put your key in it
uv run outbox check "we should probably maybe consider shipping this"
uv run outbox serve           # the same review, in a browser
```

Keys live at <https://console.typesafe.ai/keys>. The `.env` is read from the
working directory or any parent, so the same file works whether you run from
the root or from `examples/outbox/`; an exported `TYPESAFE_API_KEY` still wins
over it.

## Commands

| Command | What it does |
| --- | --- |
| `outbox check "<draft>"` | Reads a draft and says whether to send it. Takes stdin too: `pbpaste \| outbox check` |
| `outbox serve` | The desk in a browser, with the draft marked up sentence by sentence |
| `outbox demo` | Six bundled drafts, reviewed concurrently, one line each |
| `outbox models` | Which models your key can send a draft to |

`check` also takes `--to` (who is reading it), `--goal` (what you want to
happen), `--channel`, `--audience` to override the reader it inferred,
`--quick` to skip the sentence pass, and `--runs N` to read the same draft N
times and report how much the verdict moves.

## What Jev is asked

**Pass one — 25 questions, one request.** Jev reads the draft once and answers
all of them in parallel, which is the
[speculative fan-out](https://docs.typesafe.ai/patterns/fan-out) pattern: ask
everything the code might need, and let the code decide what applies.

- **[Choice](https://docs.typesafe.ai/primitives/choice)** for what the draft is
  trying to do (`request`, `decline`, `apologise`, `escalate`, …) and for what
  is most likely to go wrong if you send it as written.
- **[Score](https://docs.typesafe.ai/primitives/score)** for six dimensions —
  clarity, actionability, directness, warmth, formality, brevity. Scores land
  between levels, so 2.82 is a real answer rather than a rounding artefact.
- **[Noul](https://docs.typesafe.ai/primitives/noul)** for the checklist: is
  there an ask, a deadline, enough context; does it hedge, over-apologise,
  blame someone, read as passive-aggressive, commit you to something, carry
  something that should not be in a message at all.
- Five of the questions are **speculative**. `decline_is_final` only matters if
  the draft is a decline; `apology_repairs` only if it is an apology. They ride
  along in the same request because an extra question is close to free and a
  second round trip is not.

**Pass two — one question per sentence, one request.** This is the only place a
second request is justified, and it is justified because the questions do not
exist until pass one has answered: there is no point spending a question per
sentence on hedging in a draft that does not hedge. The draft is split in code,
each sentence is sent as a
[structured instruction](https://docs.typesafe.ai/primitives/advanced)
(`{"sentence": …, "question": …}`) with the whole draft still in the state, and
the answers are painted back onto the exact characters they were asked about.

"Which sentence carries the ask?" is answered by comparing sentences rather than
thresholding each one — every sentence in a polite request leans a little
towards yes, and only the highest one is the answer.

## What the code does with the answers

Jev never sees a verdict. It comes out of four rules you can read in an
afternoon and change in a minute:

**Bands, not targets.** Higher is not better. A draft can be too warm, too
formal, too blunt, too short. So every reader — manager, teammate, client, exec,
public channel, friend — gives each dimension a *band* it should land in and a
weight for how much missing it matters. This is
[composite scoring](https://docs.typesafe.ai/patterns/composite-scoring) where
the audience changes the target as well as the weight. It all lives in
`audience.py`.

**Confidence as a floor.** A dimension Jev is under 30% confident about is shown
but left out of the score, with the reason printed next to it. If confidence in
what the draft is even *for* drops below 0.45, the desk returns `UNREADABLE`
instead of a verdict — which is almost always a fact about the draft.
See [confidence](https://docs.typesafe.ai/confidence).

**Findings, thresholded and priced.** Each check has a threshold and a severity,
and severity has a price: a major costs 12 points, a blocker caps the score at
25 whatever else is true. Findings that only make sense for some intents — "you
never actually ask for anything" — are only applied to those intents.

**The measurement outlives the verdict.** In the browser, switching from *a
manager* to *an exec* re-runs the whole verdict against different bands and
never touches the API. The endpoint that does it, `/api/rescore`, has no
TypeSafe client in it. Nothing about the draft changed; only who is reading it,
and that was always a code decision.

## Layout

```
src/outbox/
  questions/     every question Jev is asked, both passes
    choices.py     what the draft is for, and what could go wrong
    dimensions.py  the six Score scales
    checks.py      the yes/no checklist, plus the speculative questions
    read.py        pass one, assembled into one docket and one state
    probes.py      pass two: the per-sentence questions
  desk.py        the only module that calls the API (sync, async, errors)
  reviewer.py    orchestration: pass one, pass two, batches, consistency runs
  review/        pure logic over the answers: findings, scoring, verdict
    model.py       the verdicts, and the Finding / Rail / Review dataclasses
    rules.py       the tables: which answer becomes which finding
    findings.py    applying those tables to one response
    scoring.py     rails, fit, send score, verdict
    verdict.py     assess() and rescore()
    probes.py      which sentence probes to ask, and folding the answers back
  audience.py    what each reader wants, as bands and weights
  sentences.py   splitting a draft while keeping character offsets
  render/        the terminal report, via rich
    styles.py      the shared console, colours and glyphs
    report.py      the full verdict for one draft
    summaries.py   consistency runs, a batch, the model list
  web/           FastAPI: /api/read calls Jev, /api/rescore does not
    schemas.py     request bodies
    payload.py     the JSON the browser draws, and the way back to a Review
    app.py         the routes and the static files
  cli.py         typer commands
  samples.py     drafts to try it on
  static/
    index.html     the page
    css/           tokens, base, layout, then one sheet per area of the page
    js/            compiled from web/src -- committed, so no Node is needed to run it

web/src/         the browser UI, in TypeScript
  api.ts           typed calls to the three endpoints, mirroring web/payload.py
  dom.ts           element lookup, show/hide, escaping
  elements.ts      every element the script touches, looked up once
  format.ts        pure formatting: percentages, labels, the cost line
  ui/              one module per area: composer, verdict, pills, rails,
                   findings, markup, and result (which draws them in order)
  main.ts          the state, and the wiring between events and the modules
```

The UI source is TypeScript in `web/src`. After changing it, run `pnpm build`
from the repo root (or `pnpm exec tsc -b examples/outbox/web` for this example
alone) to regenerate `src/outbox/static/js`; the compiled output is committed,
so `uv run outbox serve` works without Node installed.

## Is any of this stable?

`--runs` answers that honestly. It reads the same draft several times
concurrently, reports the spread of verdicts and send scores, and names the
answers that moved most:

```
$ outbox check "..." --runs 5 --quick

  5 independent reads

  REWRITE IT  █████ 5/5

  send score 47-48  (spread 1)

  least settled answers
  biggest risk        ±0.02
  over apologises     ±0.02

  The desk says the same thing every time.
```

A draft sitting on a threshold looks different from a confidently mediocre one,
and the difference does not show up in any single response. See the
[self-consistency cookbook](https://docs.typesafe.ai/cookbooks/consistency_noul_cookbook)
for the idea in full.

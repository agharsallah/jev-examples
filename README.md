# Jev examples

Three small, complete programs built on [TypeSafe](https://docs.typesafe.ai)'s System One
models. A courtroom, a writing desk, and an arcade. None of them are toys in the sense of
being unfinished — they all run, they all ship their whole idea, and each one is short
enough to read in a sitting.

They share one virtualenv and one lockfile, so everything runs from here.

```bash
uv sync
cp .env.example .env          # put your TYPESAFE_API_KEY in it
uv run tribunal judge "the dog ate my migration"
uv run outbox check "just circling back on this -- no rush at all!!"
uv run duel serve
uv run triage issue omnigent-ai/omnigent#8107
```

That's the whole setup. Keys live at <https://console.typesafe.ai/keys>, and the `.env` is
found from the working directory or any parent — so the examples run the same from the root
or from their own directory. An exported `TYPESAFE_API_KEY` still wins over the file.

## The three of them

### [excuse-tribunal](examples/excuse-tribunal) — a courtroom for your excuses

`tribunal judge "the train was cancelled, then my laptop died"` files charges, scores
believability, effort and drama, and passes sentence. It keeps a rap sheet, so it knows your
signature move. It can also try a git commit message against the files it actually touched,
which is a bracing experience.

> One request, twelve questions. Sentencing is plain Python that never touches the network.

### [outbox](examples/outbox) — a second opinion before you hit send

`outbox check "<draft>"` reads something you're about to send and tells you whether to send
it — twenty-five questions about the draft, then one per sentence, marked back onto the
exact characters they were asked about. `outbox serve` puts it in a browser.

> Higher is never better. Every reader — manager, teammate, exec, friend — wants each
> dimension inside a *band*, and switching reader re-runs the verdict without touching the API.

### [tetris-duel](examples/tetris-duel) — a well that plays itself, racing one you play

`duel serve` deals the same seeded pieces to both wells and puts the numbers behind every
move underneath. One API call per piece, no hand-written bot hiding anywhere. Four
difficulties, and `duel bench` says which of them actually scores.

> The step that matters isn't a bigger model — it's `board.py` counting what a player counts
> and saying it in words.

### [tetris-laya](examples/tetris-laya) — the same duel, with a local model playing

The tetris duel's board, house rules and arcade, with
[Laya](https://huggingface.co/convaiinnovations/laya-multilingual) answering on your own
machine instead of Jev over the API. It carries torch, so it stays out of the root sync:
`uv sync --all-packages`, and `uv run duel serve` then offers Laya as well as Jev: pick
Jev vs Laya, Laya vs you, or any other matchup on the page.

> A 256-token option budget against a 34-landing menu: the menu runs as heats, and the
> winners meet in a final.

### [triage](examples/triage) — any GitHub repo's issues, read and sorted

`triage issue owner/repo#123` works out the repo's own labels first — one Choice per label,
*what role does this play here?* — then asks about a hundred questions of the issue in one
request: which of those labels fit, what's missing from the report, whether a candidate is the
*same* problem or merely *related*, and what each sentence signals. `triage eval` scores it
against the labels people already applied, with those labels hidden, and draws the calibration.

> Jev doesn't explain itself, so the "why" is measured: take the strongest sentence out, ask
> again, and see how far the call moves.

## What they have in common

Different domains, same three moves. Reading one example teaches you the other two.

**Ask everything at once.** Each program sends *one* request carrying a dozen or more
questions against a single reading of the state. Jev answers them in parallel, so the twelfth
question costs almost nothing while a second round trip costs real time — the
[speculative fan-out](https://docs.typesafe.ai/patterns/fan-out) pattern. Ask everything the
code might need; let the code decide what applies.

**Three primitives do the work.**
[Choice](https://docs.typesafe.ai/primitives/choice) picks one option from a menu and hands
back a probability on every one (the bar charts you see are that distribution, not decoration).
[Score](https://docs.typesafe.ai/primitives/score) rates against a rubric and lands *between*
levels, so 2.31 is a real answer rather than a rounding artefact.
[Noul](https://docs.typesafe.ai/primitives/noul) answers yes/no as a probability.

**The code owns the verdict.** Jev never says "guilty", "rewrite it", or "drop here". It
returns numbers; sentencing, scoring and house rules are ordinary Python you can read in an
afternoon and change in a minute. That's the point of the whole repo.

**[Confidence](https://docs.typesafe.ai/confidence) is a floor, not a footnote.** Below it,
the tribunal declares a mistrial, the desk returns `UNREADABLE`, and the arcade says "Jev is
torn" — instead of dressing up a coin flip as a decision.

**Say it in words, not in numbers.** Counting and comparing are Jev's weakest ground, so the
code does the arithmetic and hands over the *finding*: not `new_gaps: 2`, but "seals 2 empty
cells that can't be reached again until the rows above clear."

## Poking at it

Every example is `questions.py` (what Jev is asked) + one module that calls the API + pure
logic over the answers + `render.py`. If you want to change behaviour, the pure-logic file is
almost always the one you want — no key required to experiment there.

| Want to | Try |
| --- | --- |
| See the numbers behind a verdict | `uv run outbox check "..." --to "an exec"` |
| Find out if any of it is stable | `uv run outbox check "..." --runs 5` |
| Watch Jev play alone | `uv run duel watch -d grandmaster --pieces 18` |
| Prove a difficulty tier is worth it | `uv run duel bench -n 50 -g 2 --seed 41` |
| Read your own priors | `uv run tribunal rap-sheet` |

Each example's README goes deeper: what Jev is asked, what the code does with the answers,
and — in tetris-duel — a question that had to be rewritten before it said anything at all.
Those post-mortems are the most useful pages here.

### The browser side

Each web UI is TypeScript in its example's `web/src/`, split into small modules — an `api.ts`
that types every request, one module per part of the page, and a `main.ts` that only wires
them together. There is no bundler: `tsc` compiles to plain ES modules in the package's
`static/js/`, which the browser loads directly. That output is committed, so the examples run
without Node; you only need it to change the UI:

```bash
pnpm install
pnpm build        # or: pnpm watch
```

Python 3.12+, `uv`, and a key. Have fun.

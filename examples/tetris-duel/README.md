# Jev vs You

A tetris-style well that plays itself, with [Jev](https://docs.typesafe.ai/models) choosing
every landing, and a second well next to it for you. Same pieces, same gravity, one
scoreboard. Code does the geometry; the judgment is a single API call per piece.

```
$ duel watch --difficulty ruthless

  ██
 ████   JEV vs YOU
  ██    a self-playing well · one API call per piece

╭─ 1400 points · 6 rows · piece 31/40 ─╮
│                                      │
│         ██                           │
│     ████████    ██                   │
│ ██████████████████████               │
│ ────────────────────                 │
╰────── Ruthless · next: J ────────────╯
╭──────────────────────── what Jev said ─────────────────────────╮
│          lands  flat, columns 7-9, lowest block on the floor   │
│           from  17 legal landings                              │
│     confidence  61%  (sure — hard drop)                        │
│         danger  1.94 / 4  Getting untidy. Uneven columns or a  │
│                 couple of buried gaps to dig out.              │
│      clear now  72%                                            │
│ holding a well  18%                                            │
│           mood  tidying up — Smoothing out that step.          │
│                                                                │
│ 61% ████████████ flat, columns 7-9, on the floor ◀             │
│ 22% ████         upright, column 10, on the floor              │
│  9% ██           flat, columns 4-6, 1 row above the floor      │
│                                                                │
│ house rules: Jev wants a clear now, and this one takes 1 row   │
╰────────────────────────────────────────────────────────────────╯
```

*(Illustrative render; the numbers in yours come from Jev.)*

## Setup

From the repo root — the examples are a uv workspace, so one `uv sync` covers them all:

```bash
uv sync
cp .env.example .env          # then put your key in it
uv run duel serve             # the arcade, in a browser
uv run duel watch -d ruthless # jev alone, in the terminal
```

Keys live at <https://console.typesafe.ai/keys>. The `.env` is read from the working
directory or any parent, so the same file works whether you run from the root or from
`examples/tetris-duel/`; an exported `TYPESAFE_API_KEY` still wins over it. The key never
leaves the server: the browser posts a well and gets a move back.

## Commands

| Command | What it does |
| --- | --- |
| `duel serve` | Opens the arcade: Jev's well on the left, yours on the right, and every number behind the move underneath |
| `duel watch` | Jev plays alone in the terminal. `--pieces`, `--seed`, `--difficulty`, `--model` |
| `duel levels` | What each difficulty actually changes |

In the browser: arrow keys move and rotate, `space` hard-drops, `P` pauses, `Enter`
restarts. Both wells are dealt the **same pieces from the same seed** and fall at the
same speed, and points come from cleared rows only — so the scoreboard is a fair
comparison and not a reflex contest.

## How it works

Per piece, `board.py` does everything a computer is good at: rotate, drop, clear, count.
It hands back every distinct legal landing — usually 9 to 34 of them — and the well each
one would leave behind. Nothing is ranked. Then one request goes to Jev with five
questions against a single reading of the board:

- **[Choice](https://docs.typesafe.ai/primitives/choice)** over *every* legal landing.
  Not a shortlist: the full menu goes in `criteria`, and the answer comes back with a
  probability on each one, which is what the bars in the browser are.
- **[Score](https://docs.typesafe.ai/primitives/score)** for how much trouble the well is
  in, on a five-level rubric from "nearly empty" to "the next bad drop ends the game".
- **[Noul](https://docs.typesafe.ai/primitives/noul)** for whether clearing rows now beats
  staying flat, and another for whether the stack is holding a column open for a bar.
- **Choice** again for the mood, which is what the commentary line reads from. Jev picks
  the mood; `duel.py` picks the words. Selecting a line beats generating one.

All five ride in one request, so the danger reading and the commentary cost almost
nothing on top of the move — the
[speculative fan-out](https://docs.typesafe.ai/patterns/fan-out) pattern, applied to a
falling block. A piece costs roughly 2k–6k input tokens depending on how many landings
are legal.

### Jev plays the piece, not just the placement

The answer that comes back is a landing — a rotation and a column. The arcade turns it
into the moves a player would make: the piece arrives at the top the way you get it,
turns the short way round to the rotation Jev asked for, walks across a column at a time,
and only then goes down. The walk is theatre; what gets written into the well is the plan,
so the animation can never drift from the move Jev chose.

How it goes down is [confidence](https://docs.typesafe.ai/confidence) again. When the
Choice distribution is concentrated — `confidence >= SURE`, 0.60 in `pilot.py` — Jev has
nothing to think about on the way down, so the piece is **hard-dropped**: it slams, the
well takes the hit, and the next request goes out sooner. Below the bar it falls at normal
gravity like everyone else, and an overruled pick never counts as sure. Hard drops get
more common as Jev is told more, so Ruthless slams roughly half its pieces and Chill, which
is guessing from shape alone, almost never does.

### Difficulty is how much Jev is told

There is no hand-written tetris bot anywhere in here, and no heuristic quietly picking
the move behind Jev's back. Difficulty changes two things, both in `pilot.py`:

| | Jev sees | House rules |
| --- | --- | --- |
| **Chill** | where the piece would land, and nothing else | off |
| **Steady** | …plus a picture of the well each landing leaves behind | off |
| **Ruthless** | …plus rows cleared, gaps buried, and how tall and ragged the stack ends up | on |

**House rules** are the policy layer, and they only ever reshuffle Jev's *own*
probabilities using Jev's *own* answers: a landing that clears rows gets a bonus scaled by
how much the `clear_now` Noul wants a clear, burying a cell costs more when the danger
Score is high, and extra height above row 12 costs more under pressure. A landing Jev
thinks is hopeless cannot win on a bonus. When the rules do move the piece, the arcade
says which rule moved it, in words — an overrule is never a mystery.

[Confidence](https://docs.typesafe.ai/confidence) is read, not ignored: a Choice spread
thinly across several landings means several landings are genuinely fine, and the UI says
"Jev is torn" instead of pretending the top of a flat distribution was a firm decision.
Under Ruthless, that is exactly when the house rules earn their keep.

## Layout

```
src/tetris_duel/
  board.py       the well, the seven pieces, every legal landing and its consequences
  questions.py   the docket: the Choice over landings, the danger Score, two Nouls, the mood
  engine.py      the only module that calls the API
  pilot.py       difficulty, and the house rules over Jev's answers
  duel.py        one piece, start to finish, shared by the browser and the terminal
  web.py         FastAPI: POST a well, get a move
  render.py      terminal theatre, via rich
  cli.py         typer commands
  static/        the arcade
```

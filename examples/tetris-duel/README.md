# Jev vs You

A tetris-style well that plays itself, with [Jev](https://docs.typesafe.ai/models) choosing
every landing, and a second well next to it for you. Same pieces, same gravity, one
scoreboard. Code does the geometry; the judgment is a single API call per piece.

```
$ duel watch --difficulty grandmaster --pieces 18

╭─ 200 points · 2 rows · piece 18/18 · 0:13 ─╮
│ ████                                       │
│ ████                                       │
│ ████                                       │
│ ██████                                     │
│ ██████                                     │
│ ██████████████                             │
│ ██████████████                             │
│ ████████████████                           │
│ ██████████████████                         │
│ ██████████████████                         │
│ ────────────────────                       │
╰────────── Grandmaster · next: O ───────────╯
╭───────────────────────── what Jev said ──────────────────────────╮
│         lands  square, columns 1-2, lowest block 8 rows above    │
│                the floor                                         │
│          from  9 legal landings                                  │
│    confidence  54%                                               │
│        danger  1.83 / 4  Getting untidy. Uneven columns or a     │
│                couple of buried gaps to dig out.                 │
│     clear now  21%                                               │
│ keep the slot  41%                                               │
│          mood  setting up a big clear — Something big is         │
│                brewing!                                          │
│                                                                  │
│ 59% ████████████ square, columns 1-2, 8 rows above the floor ◀   │
│ 17% ███          square, columns 8-9, 3 rows above the floor     │
│ 15% ███          square, columns 4-5, 5 rows above the floor     │
│  6% █            square, columns 9-10, 2 rows above the floor    │
│  1% █            square, columns 2-3, 8 rows above the floor     │
│  1% █            square, columns 5-6, 5 rows above the floor     │
╰──────────────────────────────────────────────────────────────────╯

200 points from 2 rows in 0:13 of play.
```

*(A real run, with the empty rows above the stack and some line-wrapping trimmed to fit.)*

## Setup

From the repo root — the examples are a uv workspace, so one `uv sync` covers them all:

```bash
uv sync
cp .env.example .env              # then put your key in it
uv run duel serve                 # the arcade, in a browser
uv run duel watch -d grandmaster  # jev alone, in the terminal
```

Keys live at <https://console.typesafe.ai/keys>. The `.env` is read from the working
directory or any parent, so the same file works whether you run from the root or from
`examples/tetris-duel/`; an exported `TYPESAFE_API_KEY` still wins over it. The key never
leaves the server: the browser posts a well and gets a move back.

## Hosting it on Vercel

The arcade is a plain FastAPI app, and `app.py` at the root of this example is the
entrypoint Vercel looks for. No `vercel.json` is needed:

```bash
cd examples/tetris-duel
vercel                                   # first run links a project; set the root to this folder
vercel env add TYPESAFE_API_KEY          # production, preview, or both
vercel --prod
```

Or import the repo in the Vercel dashboard and set **Root Directory** to
`examples/tetris-duel`. Vercel installs the dependencies from `pyproject.toml` and serves
the whole app, `/static` included, from one function.

The key stays server-side, the same as locally. But a public URL means anyone who finds it
is spending your quota a piece at a time, so use a key you can revoke, or put the deployment
behind [Vercel's deployment protection](https://vercel.com/docs/deployment-protection).

Netlify is not an option without a rewrite: its functions run JavaScript, TypeScript and
Go, and the game logic here is Python.

## Commands

| Command | What it does |
| --- | --- |
| `duel serve` | Opens the arcade: Jev's well on the left, yours on the right, and every number behind the move underneath |
| `duel watch` | Jev plays alone in the terminal. `--pieces`, `--seed`, `--difficulty`, `--model` |
| `duel bench` | Plays the same seeded pieces at every difficulty and prints what each scored. `--pieces`, `--games`, `--seed`, repeatable `--difficulty` |
| `duel levels` | What each difficulty actually changes |

Every piece is one request, so `duel bench -n 50 -g 2` across four difficulties is 400 of
them — cheap in money, several minutes in wall clock.

In the browser: arrow keys move and rotate, `space` hard-drops, `P` pauses, `Enter`
restarts. Both wells are dealt the **same pieces from the same seed** and fall at the same
speed, and points come from cleared rows only — so the scoreboard is a fair comparison and
not a reflex contest.

A clock under the VS badge counts the match, and each well carries its own. They stop
independently, so once one player tops out the other's keeps running, and the final card
reports all three. Pausing stops them; Jev's thinking time counts, because the well is
still on the clock while it thinks. The terminal keeps the same time: `duel watch` shows
the match clock in the panel title, and `duel bench` prints seconds per piece beside tokens
per piece.

## How it works

Per piece, `board.py` does everything a computer is good at: rotate, drop, clear, count.
It hands back every distinct legal landing — usually 9 to 34 of them — the well each one
would leave behind, how the piece would sit on what is already there, and what the next
piece could do afterwards. Nothing is ranked. Then one request goes to Jev with four
questions — five on Grandmaster — against a single reading of the board:

- **[Choice](https://docs.typesafe.ai/primitives/choice)** over *every* legal landing.
  Not a shortlist: the full menu goes in `criteria`, and the answer comes back with a
  probability on each one, which is what the bars above are.
- **[Score](https://docs.typesafe.ai/primitives/score)** for how much trouble the well is
  in, on a five-level rubric from "nearly empty" to "the next bad drop ends the game".
- **[Noul](https://docs.typesafe.ai/primitives/noul)** for whether clearing rows now beats
  staying flat, and — on Grandmaster — one more asking whether a *named* column is worth
  leaving empty for a four-row clear.
- **Choice** again for the mood, which is what the commentary line reads from. Jev picks
  the mood; `duel.py` picks the words. Selecting a line beats generating one.

They all ride in one request, so the danger reading and the commentary cost almost nothing
on top of the move — the [speculative fan-out](https://docs.typesafe.ai/patterns/fan-out)
pattern, applied to a falling block. A piece costs roughly 1.5k input tokens on Chill and
6k on Grandmaster, and lands in about a second.

### Say it in words, not in numbers

Everything above the first difficulty is a fact code worked out and then *phrased*. Jev is
[not a calculator](https://docs.typesafe.ai/model-jaggedness/jev-1.13#math-and-numbers) —
counting and comparing are its weakest ground, and semantic descriptions beat numeric ones
— so `board.py` does the arithmetic and hands over the finding:

| Instead of | Jev is told |
| --- | --- |
| `new_gaps: 2, tallest: 9, roughness: 11` | "Bridges a dip and seals 2 empty cells underneath, which cannot be reached again until the rows above clear. Leaves the stack mid-height and ragged." |
| `heights: [4,4,4,7,7,2,0,0,0,3]` | "Column 7 is a single-wide slot 4 deep: only a standing bar reaches the bottom of it." |
| the next piece's letter, and good luck | "The I would then have 3 clean landings out of 17, and the best of them completes 2 rows." |

The same rule decides what is *left out*. A big state full of things the decision does not
need [costs accuracy](https://docs.typesafe.ai/model-jaggedness/jev-1.13#large-state-full-of-irrelevant-detail),
so the board picture is trimmed to the part with anything in it, and the ground reading,
the row targets and the slot question only appear at the tiers whose policy reads them.

Two plies happen the same way. Asking Jev to imagine the well after this piece and then
imagine it again is exactly the
[indirection](https://docs.typesafe.ai/model-jaggedness/jev-1.13#indirection) it is worst
at, so `prospects()` plays the next piece into every resulting well in code — about 700
simulated drops, 7ms — and each option simply states what it found.

**A question that had to be rewritten.** The first version of the slot question asked
whether "the stack is keeping a clean column open, the way a player does while waiting for
a bar". Over a whole match the answers sat between 0.32 and 0.56: no answer at all. It was
asking Jev to read an *intention* off a board, a hop it cannot make. Naming the column, its
depth, and how many rows are already complete except for it turned it into a question about
something visible, and the answers started moving — and the guard with them.

### Difficulty is how much Jev is told

There is no hand-written tetris bot anywhere in here, and no heuristic quietly picking the
move behind Jev's back. A difficulty is a row in `pilot.py`, and it sets how much of each
landing Jev is shown and what the house rules are allowed to do with the answer:

| | Jev sees | House rules |
| --- | --- | --- |
| **Chill** | where the piece would land, and nothing else | off |
| **Steady** | …plus a picture of the well each landing leaves behind | off |
| **Ruthless** | …plus how the piece sits on what is there, and a reading of the ground | on |
| **Grandmaster** | …plus what the next piece could do afterwards, and the rows closest to completing | on, including the slot guard |

**House rules** are the policy layer, and they only ever reshuffle Jev's *own* probabilities
using Jev's *own* answers: a landing that clears rows gets a bonus scaled by how much the
`clear_now` Noul wants a clear, burying a cell costs more when the danger Score is high, and
extra height above row 12 costs more under pressure. The clear bonus is **square, not
linear**, because the game pays that way — four rows at once are worth 800 and four rows one
at a time are worth 400 — so a cheap single cannot outbid the shape that sets up a bigger
clear. A landing Jev thinks is hopeless cannot win on a bonus. When the rules do move the
piece, the arcade says which rule moved it, in words — an overrule is never a mystery.

The **slot guard** is the one rule with a question of its own, and it is only on under
Grandmaster. Code picks the column worth keeping empty — a slot that already exists, or
failing that the right-hand edge — and asks Jev, about that column by number, whether it is
worth leaving alone for now. While the answer is yes and the well is not about to lose,
filling that column costs a landing `WELL_GUARD`, scaled down by how many rows it would
take: a four-row clear pays nothing, because that is what the slot was being kept for.

The column is chosen for **stability**, not cleverness. Picking the emptiest column each
turn reads better and plays worse: the answer moves as the stack grows, the plan moves with
it, and no column is ever left alone long enough to become a well. The right-hand edge does
not move.

Waiting for a bar is a bet, so the question says what the odds are. Pieces are dealt in bags
of seven — one of each shape — so **one piece in seven is the straight bar**, and a dozen
pieces can go by between one bar and the next. The question carries that, plus how many
pieces have gone by since the last one, and the depth of the slot in rows. Before it did,
the answers drifted to a flat "no" as soon as the stack looked busy; with the wait spelled
out they hold above 0.5 for as long as the stack can afford it.

[Confidence](https://docs.typesafe.ai/confidence) is read, not ignored: a Choice spread
thinly across several landings means several landings are genuinely fine, and the UI says
"Jev is torn" instead of pretending the top of a flat distribution was a firm decision.
Under the top two tiers, that is exactly when the house rules earn their keep.

### Jev plays the piece, not just the placement

The answer that comes back is a landing — a rotation and a column. The arcade turns it into
the moves a player would make: the piece arrives at the top the way you get it, turns the
short way round to the rotation Jev asked for, walks across a column at a time, and only
then goes down. The walk is theatre; what gets written into the well is the plan, so the
animation can never drift from the move Jev chose.

How it goes down is confidence again. When the Choice distribution is concentrated —
`confidence >= SURE`, 0.60 in `pilot.py` — Jev has nothing to think about on the way down,
so the piece is **hard-dropped**: it slams, the well takes the hit, and the next request
goes out sooner. Below the bar it falls at normal gravity like everyone else, and an
overruled pick never counts as sure. Hard drops get more common as Jev is told more, so
Ruthless slams roughly half its pieces and Chill, guessing from shape alone, almost never
does.

### Does any of it actually score more?

`duel bench` plays the same seeded pieces at each difficulty, so the only thing that differs
between two rows is what Jev was told and what the house rules did with the answer. The
ladder, two matches per tier, 50 pieces each:

```
$ duel bench -n 50 -g 2 --seed 41

┏━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ difficulty  ┃ points ┃ rows ┃ clears           ┃ survived ┃ tokens/piece ┃
┡━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Chill       │      0 │  0.0 │ —                │      0/2 │         1744 │
│ Steady      │     50 │  0.5 │ 1×1              │      0/2 │         3358 │
│ Ruthless    │   2550 │ 13.5 │ 1×10 2×5 3×1 4×1 │      2/2 │         5314 │
│ Grandmaster │   2050 │ 12.5 │ 1×13 2×6         │      2/2 │         6094 │
└─────────────┴────────┴──────┴──────────────────┴──────────┴──────────────┘
```

**The ground reading is the whole game.** Steady gets a picture of the well after every
landing and still tops out before 50 pieces, every time. Ruthless gets the same picture plus
a sentence on how the piece would sit on what is already there, and the ground read out in
words — and survives every match with fifty times the score. That step is not a bigger model
or a cleverer rule: it is `board.py` counting what a player counts, and saying it in the
language Jev is good at.

**The second ply pays, but two matches cannot see it.** In the table above Grandmaster
*lost*. Six matches per tier on six fresh seeds say otherwise:

```
$ duel bench -d ruthless -d grandmaster -n 50 -g 6 --seed 101

┏━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ difficulty  ┃ points ┃ rows ┃ clears            ┃ survived ┃ tokens/piece ┃
┡━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Ruthless    │   2350 │ 13.3 │ 1×34 2×14 3×6     │      6/6 │         5339 │
│ Grandmaster │   3167 │ 16.3 │ 1×45 2×20 3×3 4×1 │      6/6 │         5892 │
└─────────────┴────────┴──────┴───────────────────┴──────────┴──────────────┘
```

Grandmaster won **every one of the six paired seeds** — 3000/2000, 2700/2300, 3900/2200,
3100/2600, 3700/2500, 2600/2500 — for +35% on points and 10% more tokens a piece. It also
landed the only four-row clear of the run. Six is still not many, and the honest summary is
that the effect is real and its size is not yet pinned down; `duel bench -g 20` is the
experiment.

Worth keeping in view: Ruthless's six scores land between 2000 and 2600, a remarkably steady
player, and its worst match still beats everything below it on the ladder. The variance that
made a two-match comparison useless is almost all Grandmaster's, and it is the variance of a
player that sometimes gets its bet paid.

*(Both runs predate the `sec/piece` column the table now prints beside `tokens/piece`.)*

## Layout

```
src/tetris_duel/
  board.py       the well, the seven pieces, every legal landing and its consequences
  questions.py   the docket, and the words the ground and each landing are described in
  engine.py      the only module that calls the API
  pilot.py       difficulty, and the house rules over Jev's answers
  duel.py        one piece, start to finish, plus self-play for the terminal and the bench
  web.py         FastAPI: POST a well, get a move
app.py           Vercel entrypoint, re-exports web.app
  render.py      terminal theatre, via rich
  cli.py         typer commands
  static/        the arcade
```

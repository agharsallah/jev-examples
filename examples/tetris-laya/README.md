# Laya vs You

The [tetris duel](../tetris-duel), with a local model at the controls instead of Jev:
[`convaiinnovations/laya-multilingual`](https://huggingface.co/convaiinnovations/laya-multilingual),
a 322M-parameter System 1 decision model that runs on your machine. Same board, same legal
landings, same house rules, same arcade. No API key, and no network once the checkpoint is
downloaded.

## Setup

Laya pulls in `torch` and `transformers`, so this example is a workspace member but not part
of the root `uv sync`. Ask for it by name:

```bash
uv sync --package tetris-laya
uv run --package tetris-laya laya-duel serve                # the arcade, Laya vs you, on :8001
uv run --package tetris-laya laya-duel watch -d grandmaster  # laya alone, in the terminal
```

The first run downloads the checkpoint (about 1.3 GB) into the Hugging Face cache. It runs
on CUDA, Apple's MPS or the CPU, whichever it finds; `LAYA_DEVICE=cpu` forces one.
`--model` (or `LAYA_MODEL`) takes any other Laya checkpoint, a repo id or a local path, such
as one you fine-tuned.

| Command | What it does |
| --- | --- |
| `laya-duel serve` | The `duel serve` arcade, opened on Laya vs you; the page switches to any matchup |
| `laya-duel serve --versus` | The same arcade, opened on Laya vs Jev |
| `laya-duel versus` | The same match in the terminal, both wells side by side. `--pieces`, `--seed`, `--difficulty`, `--model`, `--jev-model` |
| `laya-duel watch` | Laya plays alone in the terminal. `--pieces`, `--seed`, `--difficulty`, `--model` |
| `laya-duel bench` | Same seeds as `duel bench`, so the two tables are the same games |
| `laya-duel levels` | What each difficulty changes for Laya |

### One arcade, any matchup

This package registers Laya as a player of the tetris duel (the `tetris_duel.players` entry
point), so there is only one arcade: `duel serve` and `laya-duel serve` are the same app, and
the seat pickers at the top choose Laya, Jev or you for each well.

### Laya vs Jev

Both versus modes put Jev in the other well, so they need the `TYPESAFE_API_KEY` from the
[root setup](../../README.md) in your `.env`; Laya still runs locally. Both players get the
same seeded pieces, the same gravity and the same difficulty, run the same board code and
the same house rules, and each has its own card of what it said about its last piece. The
only difference between the wells is the model reading them, and how its questions are put.
Every Jev piece is one API request, as it is in `duel`.

## What is reused, and what is not

Everything that is not the asking comes from `tetris-duel`, imported rather than copied:
`board` for the geometry and every finding it phrases, `pilot.py` for the house rules and
the slot guard, `selfplay.py` and `payload.py` for whole matches and what the scoreboard
draws, `render.py` for the terminal, and the whole arcade. The Jev harness takes the player as
a parameter — `self_play(play=...)`, and a `Player` registered for the arcade — and this
package supplies a `play_piece` with the same signature:

```
src/tetris_laya/
  engine.py      loads the checkpoint once; one forward pass per call
  levels.py      Laya's difficulty ladder: same keys and gravity as Jev's
  phrasing.py    the state, most important first, and each landing in one line
  questions.py   the docket, cut down to Laya's budget, and the heats
  play.py        heats, the final, and Laya's answers read back into the pilot's shape
  player.py      Laya's seat in the arcade, registered as an entry point
  cli/           the commands: solo.py (watch, bench, levels), serve.py, versus.py
```

## Fitting the question to the model

Laya takes the same kind of docket Jev does — a state, and typed `choice`, `score` and
`noul` questions answered in one pass — but it is a small encoder with a fixed budget, and
the model card is candid about where it is weak. Three things changed.

**The menu runs as heats.** Each question gets 256 tokens for its instructions and all of
its options, and each option is cut at 48. A well can offer 34 landings, which leaves seven
tokens a landing: not enough to say which column. So `questions.heats()` packs the menu, in
order, into questions that fit; every heat of a round goes in one forward pass; the winners
meet in the next round, until one question holds the field. Code only decides who races
whom. Each landing's probability is its share of its own heat times its heat winner's
probability in the round above, so they still sum to one and the house rules can read them
exactly as they read Jev's. A full menu is two or three passes.

**Each landing is a line, not a paragraph.** Jev is told "Bridges a dip and seals 2 empty
cells underneath, which cannot be reached again until the rows above clear." Laya is told
"seals 2 holes". The findings are the same ones `board.py` works out for Jev; only the
phrasing is shorter. A picture of the well afterwards is about 60 tokens, so on Steady it
becomes "leaves it mid and bumpy".

**No `score`, no `noul`.** The model card reports a position bias on `score` (it rarely picks
the first level) and a `noul` that can under-report "true", and suggests a two-option
`choice` with neutral keys instead. So the danger rubric is a five-way choice whose expected
level is read back as the score, and the yes-or-no questions are `A`/`B` choices. The state
goes most-important-first, because Laya truncates it at 1024 tokens.

## How it plays

Badly, for now, and the bench says exactly how badly. The same seeds as the Jev table in
[tetris-duel](../tetris-duel#does-any-of-it-actually-score-more), on an M1 Pro over MPS:

```
$ laya-duel bench -n 50 -g 2 --seed 41

┏━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ difficulty  ┃ points ┃ rows ┃ clears  ┃ survived ┃ tokens/piece ┃ sec/piece ┃
┡━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Chill       │      0 │  0.0 │ —       │      0/2 │         1690 │       0.3 │
│ Steady      │      0 │  0.0 │ —       │      0/2 │         1794 │       0.3 │
│ Ruthless    │    700 │  6.0 │ 1×9 3×1 │      2/2 │         2891 │       0.4 │
│ Grandmaster │    600 │  4.0 │ 1×2 3×2 │      0/2 │         4489 │       0.7 │
└─────────────┴────────┴──────┴─────────┴──────────┴──────────────┴───────────┘
```

Jev, on the same pieces, scores 2550 on Ruthless and 2050 on Grandmaster. The more useful
comparison is against nobody. Replace Laya's landing probabilities with a flat distribution,
keep its danger, clear-now and slot answers, and let the house rules choose:

| Ruthless, seed 41 / 42 | points | overruled |
| --- | --- | --- |
| Laya's landing pick | 600 / 800 | 34 / 28 of 50 |
| flat pick, same house rules | 2700 / 1700 | 47 / 49 of 50 |

Zero-shot, Laya's pick is worse than no pick at all: where it has a preference, the
preference is wrong often enough to cost points, and on Chill and Steady — no house rules —
it tops out without clearing a row. Its probabilities are also nearly flat (landing
confidence around 0.05), so on the top two tiers the house rules overrule most pieces anyway.
Laya is deterministic, so these numbers reproduce exactly.

That is the honest starting point, not the end of it: the harness, the heats and the bench
are all here, so a better docket or a fine-tuned checkpoint shows up as a better row.

## Limits

- **Laya ships uncalibrated.** Its probabilities have not been fitted to this task, so the
  confidence thresholds in `pilot.py` (`TORN`, `SURE`) mean something different here than they
  do for Jev.
- **Not hostable on Vercel.** The Jev arcade is a thin server over an API; this one carries
  torch and a 1.3 GB checkpoint. Run it on a machine, or a container with a GPU.
- **Zero-shot is the weak case.** The model card says fine-tuning for a specific workflow is
  where the capability comes from. A checkpoint trained on tetris positions goes straight
  into `--model`.

# The Excuse Tribunal

A courtroom for your excuses. [Jev](https://docs.typesafe.ai/models) sits as judge, and
plain Python passes sentence.

```
$ tribunal judge "The train was cancelled, then my laptop died, then honestly I forgot"

        __
   ____/  \____      THE EXCUSE TRIBUNAL
  |____________|     presided over by Jev
       |  |
       |__|          all rise

╭─ the accused states ───────────────────────────────────────────────────────╮
│ The train was cancelled, then my laptop died, then honestly I forgot       │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ RELEASED UNDER SUSPICION ─────────────────────────────────────────────────╮
│ Plausible, but the accused points the finger too readily.                  │
│                                                                            │
│      believability ██████████████·········· 2.31 / 4                       │
│             effort ███████················· 1.12 / 4                       │
│              drama ████████████████········ 2.74 / 4                       │
│     survives up to ████████████············ Survives a colleague, but      │
│                                             not a manager                  │
│                                                                            │
│ reading of the charges                                                     │
│ ✗   Blamed a machine that cannot defend itself 91%                         │
│ ✗   Shows signs of prior use                   66%                         │
│ ✓   Accepted responsibility                    77%                         │
│                                                                            │
│ filed as: transit saga  (confidence 64%)                                   │
│       transit saga ██████████████·········· 58%                            │
│    blame the cloud ██████████·············· 42%                            │
╰────────────────────────────────────────────────────────────────────────────╯

 SENTENCE  You write the meeting notes for a week.
  (believability confidence 71%)
```

*(Numbers above are an illustrative render; yours come from Jev.)*

## Setup

From the repo root — the examples are a uv workspace, so one `uv sync` covers them all:

```bash
uv sync
cp .env.example .env          # then put your key in it
uv run tribunal judge "the dog ate my migration"
```

Keys live at <https://console.typesafe.ai/keys>. The `.env` is read from the working
directory or any parent, so the same file works whether you run from the root or from
`examples/excuse-tribunal/`; an exported `TYPESAFE_API_KEY` still wins over it. The SDK
picks the key up from the environment on its own, and calls `jev-latest` unless you
pass `--model`.

## Commands

| Command | What it does |
| --- | --- |
| `tribunal judge "<excuse>"` | Tries an excuse. Accepts stdin too: `echo "..." \| tribunal judge` |
| `tribunal commit [--rev HEAD]` | Tries a git commit message against the files it actually touched |
| `tribunal rap-sheet` | Your priors: every hearing, your average believability, your signature move |
| `tribunal expunge` | Deletes the record (`~/.excuse-tribunal/rap-sheet.jsonl`) |

`judge` also takes `--context` (what you were supposed to do) and `--audience`
(who you are telling), which go into the state as separate fields rather than
being smuggled into the excuse itself.

## How it works

One request, twelve questions. Jev reads the state once and evaluates every
question against it in parallel, so the whole docket costs barely more than a
single question — the [speculative fan-out](https://docs.typesafe.ai/patterns/fan-out)
pattern, applied to petty personal failure.

- **[Choice](https://docs.typesafe.ai/primitives/choice)** picks the excuse
  archetype (`transit_saga`, `blame_the_cloud`, `cosmic_forces`, …) and returns a
  probability for every one, which is what the little bar chart is showing.
- **[Score](https://docs.typesafe.ai/primitives/score)** rates believability,
  effort, drama, and the most demanding audience the excuse could survive. Scores
  land between levels, so 2.31 is a real answer, not a rounding artefact.
- **[Noul](https://docs.typesafe.ai/primitives/noul)** handles the yes/no charges:
  did you blame a person, blame a machine, accept fault, offer a checkable detail.
  Each comes back as a probability, and the ones above 0.5 are read out in court.

Sentencing lives in `verdict.py` and never touches the network. Aggravating
findings drag the sentence down, mitigating ones lift it, and if Jev's
confidence in believability drops below 0.5 the court declares a **mistrial**
instead of guessing — the [confidence](https://docs.typesafe.ai/confidence) floor
doing exactly the job it is there for.

## Layout

```
src/excuse_tribunal/
  questions.py   the docket: every Choice, Score and Noul
  tribunal.py    the only module that calls the API
  verdict.py     pure sentencing logic over the answers
  render.py      courtroom theatre, via rich
  rap_sheet.py   your permanent record, as JSON lines
  cli.py         typer commands
```

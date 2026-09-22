# Jev examples

Small, complete programs built on [TypeSafe](https://docs.typesafe.ai)'s System One
models. They share one virtualenv and one lockfile, so everything runs from here.

```bash
uv sync
cp .env.example .env          # put your TYPESAFE_API_KEY in it
uv run tribunal judge "the dog ate my migration"
uv run outbox check "just circling back on this -- no rush at all!!"
uv run duel serve
```

The `.env` is found from the working directory or any parent, so the examples run the
same from the root or from their own directory. Keys: <https://console.typesafe.ai/keys>.

| Example | What it is |
| --- | --- |
| [excuse-tribunal](examples/excuse-tribunal) | A courtroom for your excuses: one request, twelve questions, sentencing in plain Python |
| [outbox](examples/outbox) | A second opinion before you hit send: twenty-five questions about a draft, then one per sentence, and a verdict your code owns |
| [tetris-duel](examples/tetris-duel) | A well that plays itself, one API call per piece, racing a well you play yourself |

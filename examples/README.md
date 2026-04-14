# PitGPT Examples

These files are intentionally small and safe to run from a clean checkout.

Run deterministic analysis without an API key:

```sh
uv run --python 3.12 pitgpt analyze \
  --protocol examples/protocol.json \
  --observations examples/observations.csv \
  --format json
```

Run research ingestion with an OpenRouter API key:

```sh
OPENROUTER_API_KEY=... uv run --python 3.12 pitgpt ingest \
  --query "Compare two moisturizers for evening skin comfort" \
  --doc examples/moisturizer-note.md \
  --format json
```

Without `OPENROUTER_API_KEY`, ingestion exits with `OPENROUTER_API_KEY not set`.

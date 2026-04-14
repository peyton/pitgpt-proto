# Choose Your Path

PitGPT is local-first. You can run the example, start a template, or generate a
protocol from a question.

## Web

```sh
just setup
just serve
just web-dev
```

Open the Vite URL and choose:

- **Run example**: loads bundled observations and shows a completed result.
- **Start template**: no API key needed; lock labels, then check in daily.
- **Ask question**: needs `OPENROUTER_API_KEY` to generate a protocol.

The web app stores trials in browser localStorage. Use Settings to export or
restore JSON. Completed trials can also export an appointment brief Markdown
file with protocol details, timeline notes, adverse events, uncertainty, and
questions to bring to a clinician.

PitGPT can frame low-risk routines that touch a condition when the plan is
reversible, non-urgent, and does not change medications or replace care.
Medication changes, urgent symptoms, invasive interventions, and diagnosis
questions are blocked or routed away from self-serve protocol generation.

## CLI

Analyze the bundled example without an API key:

```sh
pitgpt demo analyze
```

Create a local trial folder:

```sh
pitgpt trial init --template skincare --output-dir my-trial
```

Generate a schedule:

```sh
pitgpt trial randomize --protocol my-trial/protocol.json --seed 123
```

Append a check-in:

```sh
pitgpt checkin add \
  --observations my-trial/observations.csv \
  --day 1 \
  --date 2026-01-01 \
  --condition A \
  --score 7
```

Validate before analysis:

```sh
pitgpt validate --protocol my-trial/protocol.json --observations my-trial/observations.csv
```

## API

Start the API:

```sh
just serve
```

Useful read/demo endpoints:

- `GET /templates`
- `POST /schedule`
- `GET /analyze/example`

`POST /ingest` requires `OPENROUTER_API_KEY`. Missing configuration returns a
structured `503`.

## TUI

```sh
just tui
```

The TUI is useful for local file-based analysis. Use the CLI or web app when
you want template initialization, schedule export, or import/restore.

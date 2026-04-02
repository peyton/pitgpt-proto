import asyncio
import json
import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pitgpt.core.analysis import analyze
from pitgpt.core.ingestion import ingest
from pitgpt.core.llm import LLMClient
from pitgpt.core.models import Observation

app = typer.Typer(name="pitgpt", help="PitGPT — personal clinical trial machine")
benchmark_app = typer.Typer(name="benchmark", help="Run and report on benchmarks")
app.add_typer(benchmark_app, name="benchmark")

console = Console()

FORMAT_OPTION = typer.Option("pretty", help="Output format: json, table, pretty")


def _detect_format(fmt: str) -> str:
    if fmt != "pretty":
        return fmt
    if not sys.stdout.isatty():
        return "json"
    return "pretty"


def _read_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(1)
    return p.read_text()


def _get_model(model: str | None) -> str:
    if model:
        return model
    return os.environ.get("PITGPT_DEFAULT_MODEL", "anthropic/claude-sonnet-4")


def _get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        console.print("[red]OPENROUTER_API_KEY not set[/red]")
        raise typer.Exit(1)
    return key


@app.command()
def ingest_cmd(
    query: str = typer.Option(..., "--query", "-q", help="Natural language question"),
    doc: list[str] = typer.Option(  # noqa: B008
        [], "--doc", "-d", help="Document file paths"
    ),
    model: str | None = typer.Option(None, "--model", "-m", help="Model identifier"),
    format: str = FORMAT_OPTION,
):
    """Run research ingestion and produce a protocol or safety decision."""
    fmt = _detect_format(format)
    model_id = _get_model(model)
    api_key = _get_api_key()
    documents = [_read_file(d) for d in doc]
    client = LLMClient(model=model_id, api_key=api_key)
    result = asyncio.run(ingest(query, documents, client))

    if fmt == "json":
        console.print_json(result.model_dump_json())
    else:
        _print_ingestion_result(result)


@app.command()
def analyze_cmd(
    protocol: str = typer.Option(..., "--protocol", "-p", help="Protocol JSON file"),
    observations: str = typer.Option(..., "--observations", "-o", help="Observations CSV file"),
    format: str = FORMAT_OPTION,
):
    """Analyze a completed trial and produce a result card."""
    fmt = _detect_format(format)
    proto_data = json.loads(_read_file(protocol))
    obs_data = _parse_observations_csv(_read_file(observations))
    result = analyze(proto_data, obs_data)

    if fmt == "json":
        console.print_json(result.model_dump_json())
    else:
        _print_result_card(result)


@benchmark_app.command("run")
def benchmark_run(
    model: str | None = typer.Option(None, "--model", "-m"),
    track: str = typer.Option("all", "--track", "-t", help="ingestion, analysis, or all"),
    cases: str | None = typer.Option(None, "--cases", "-c", help="Comma-separated case IDs"),
    format: str = FORMAT_OPTION,
):
    """Run benchmark suite against a model."""
    from benchmarks.runner import run_benchmark

    fmt = _detect_format(format)
    case_filter = [c.strip() for c in cases.split(",")] if cases else None
    model_id = _get_model(model)
    results = asyncio.run(run_benchmark(model_id, track, case_filter))

    if fmt == "json":
        console.print_json(json.dumps(results, indent=2))
    else:
        _print_benchmark_results(results)


@benchmark_app.command("report")
def benchmark_report(
    output: str | None = typer.Option(None, "--output", "-o"),
):
    """Compare benchmark runs across models."""
    from benchmarks.report import generate_report

    report = generate_report()
    if output:
        Path(output).write_text(json.dumps(report, indent=2))
        console.print(f"[green]Report written to {output}[/green]")
    else:
        _print_benchmark_report(report)


def _parse_observations_csv(content: str) -> list[Observation]:
    lines = content.strip().split("\n")
    if not lines:
        return []
    header = [h.strip() for h in lines[0].split(",")]
    observations = []
    for line in lines[1:]:
        if not line.strip():
            continue
        values = [v.strip() for v in line.split(",")]
        row = dict(zip(header, values, strict=False))
        obs = Observation(
            day_index=int(row.get("day_index", 0)),
            date=row.get("date", ""),
            condition=row.get("condition", ""),
            primary_score=float(row["primary_score"]) if row.get("primary_score") else None,
            irritation=row.get("irritation", "no"),
            adherence=row.get("adherence", "yes"),
            note=row.get("note", ""),
            is_backfill=row.get("is_backfill", "no"),
            backfill_days=float(row["backfill_days"]) if row.get("backfill_days") else None,
        )
        observations.append(obs)
    return observations


def _print_ingestion_result(result):
    tier_colors = {"GREEN": "green", "YELLOW": "yellow", "RED": "red"}
    color = tier_colors.get(result.safety_tier.value, "white")

    content_parts = [
        f"[bold]Decision:[/bold] {result.decision.value}",
        f"[bold]Safety Tier:[/bold] [{color}]{result.safety_tier.value}[/{color}]",
        f"[bold]Evidence Quality:[/bold] {result.evidence_quality.value}",
        f"[bold]Evidence Conflict:[/bold] {result.evidence_conflict}",
    ]

    if result.protocol:
        p = result.protocol
        content_parts.extend(
            [
                "",
                "[bold underline]Protocol[/bold underline]",
                f"  Template: {p.template}",
                f"  Duration: {p.duration_weeks} weeks",
                f"  Block Length: {p.block_length_days} days",
                f"  Cadence: {p.cadence}",
                f"  Washout: {p.washout}",
                f"  Outcome: {p.primary_outcome_question}",
            ]
        )
        if p.screening:
            content_parts.append(f"  Screening: {p.screening}")
        if p.warnings:
            content_parts.append(f"  Warnings: {p.warnings}")

    if result.block_reason:
        content_parts.append(f"\n[red]Block Reason:[/red] {result.block_reason}")

    content_parts.append(f"\n[italic]{result.user_message}[/italic]")

    console.print(
        Panel("\n".join(content_parts), title="PitGPT Ingestion Result", border_style=color)
    )


def _print_result_card(result):
    grade_colors = {"A": "green", "B": "cyan", "C": "yellow", "D": "red"}
    color = grade_colors.get(result.quality_grade.value, "white")

    content_parts = [
        f"[bold]Quality Grade:[/bold] [{color}]{result.quality_grade.value}[/{color}]",
    ]

    if result.mean_a is not None:
        content_parts.extend(
            [
                f"[bold]Mean A:[/bold] {result.mean_a:.2f}  |  "
                f"[bold]Mean B:[/bold] {result.mean_b:.2f}",
                f"[bold]Difference:[/bold] {result.difference:+.2f}",
                f"[bold]95% CI:[/bold] [{result.ci_lower:.2f}, {result.ci_upper:.2f}]",
            ]
        )

    content_parts.extend(
        [
            f"[bold]Observations:[/bold] A={result.n_used_a}, B={result.n_used_b}",
            f"[bold]Adherence:[/bold] {result.adherence_rate:.1%}",
            f"[bold]Days Logged:[/bold] {result.days_logged_pct:.1%}",
            f"[bold]Early Stop:[/bold] {result.early_stop}",
            "",
            f"[italic]{result.summary}[/italic]",
            "",
            f"[dim]{result.caveats}[/dim]",
        ]
    )

    console.print(Panel("\n".join(content_parts), title="PitGPT Result Card", border_style=color))


def _print_benchmark_results(results: dict):
    table = Table(title=f"Benchmark Results — {results.get('model', 'unknown')}")
    table.add_column("Case", style="bold")
    table.add_column("Track")
    table.add_column("Score", justify="right")
    table.add_column("Details")

    for case in results.get("cases", []):
        score = case.get("score", 0)
        color = "green" if score >= 0.8 else "yellow" if score >= 0.5 else "red"
        table.add_row(
            case["case_id"],
            case["track"],
            f"[{color}]{score:.2f}[/{color}]",
            case.get("details", ""),
        )

    console.print(table)

    summary = results.get("summary", {})
    console.print(
        f"\n[bold]Overall:[/bold] {summary.get('mean_score', 0):.2f} "
        f"({summary.get('pass_count', 0)}/{summary.get('total', 0)} passed)"
    )


def _print_benchmark_report(report: dict):
    table = Table(title="Benchmark Comparison Report")
    table.add_column("Model", style="bold")
    table.add_column("Track A", justify="right")
    table.add_column("Track B", justify="right")
    table.add_column("Overall", justify="right")
    table.add_column("Timestamp")

    for run in report.get("runs", []):
        table.add_row(
            run["model"],
            f"{run.get('track_a_score', 0):.2f}",
            f"{run.get('track_b_score', 0):.2f}",
            f"{run.get('overall_score', 0):.2f}",
            run.get("timestamp", ""),
        )

    console.print(table)


if __name__ == "__main__":
    app()

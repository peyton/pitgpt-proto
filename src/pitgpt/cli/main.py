import asyncio
import json
import sys
from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pitgpt.core.analysis import analyze
from pitgpt.core.ingestion import ingest
from pitgpt.core.io import load_analysis_protocol, parse_observations_csv, read_text_file
from pitgpt.core.llm import LLMClient
from pitgpt.core.settings import load_settings

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


def _read_file_or_exit(path: str) -> str:
    try:
        return read_text_file(path)
    except FileNotFoundError as e:
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(1) from e


def _get_model(model: str | None) -> str:
    if model:
        return model
    return load_settings().default_model


def _get_client(model_id: str) -> LLMClient:
    settings = load_settings()
    key = settings.openrouter_api_key
    if not key:
        console.print("[red]OPENROUTER_API_KEY not set[/red]")
        raise typer.Exit(1)
    return LLMClient(
        model=model_id,
        api_key=key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout_s=settings.llm_timeout_s,
    )


@app.command("ingest")
def ingest_command(
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
    documents = [_read_file_or_exit(d) for d in doc]
    client = _get_client(model_id)
    result = asyncio.run(ingest(query, documents, client))

    if fmt == "json":
        console.print_json(result.model_dump_json())
    else:
        _print_ingestion_result(result)


@app.command("analyze")
def analyze_command(
    protocol: str = typer.Option(..., "--protocol", "-p", help="Protocol JSON file"),
    observations: str = typer.Option(..., "--observations", "-o", help="Observations CSV file"),
    format: str = FORMAT_OPTION,
):
    """Analyze a completed trial and produce a result card."""
    fmt = _detect_format(format)
    try:
        proto_data = load_analysis_protocol(protocol)
        obs_data = parse_observations_csv(_read_file_or_exit(observations))
    except FileNotFoundError as e:
        console.print(f"[red]File not found: {e.filename}[/red]")
        raise typer.Exit(1) from e
    except (json.JSONDecodeError, ValidationError) as e:
        console.print(f"[red]Invalid input: {e}[/red]")
        raise typer.Exit(1) from e
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
    from pitgpt.benchmarks.runner import run_benchmark

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
    from pitgpt.benchmarks.report import generate_report

    report = generate_report()
    if output:
        Path(output).write_text(json.dumps(report, indent=2))
        console.print(f"[green]Report written to {output}[/green]")
    else:
        _print_benchmark_report(report)


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

    verdict_display = {
        "favors_a": "Favors A",
        "favors_b": "Favors B",
        "inconclusive": "Inconclusive",
        "insufficient_data": "Insufficient Data",
    }

    content_parts = [
        f"[bold]Quality Grade:[/bold] [{color}]{result.quality_grade.value}[/{color}]",
        f"[bold]Verdict:[/bold] {verdict_display.get(result.verdict, result.verdict)}",
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
        if result.cohens_d is not None:
            content_parts.append(f"[bold]Effect Size:[/bold] Cohen's d = {result.cohens_d:+.2f}")

    content_parts.extend(
        [
            f"[bold]Observations:[/bold] A={result.n_used_a}, B={result.n_used_b}",
            f"[bold]Adherence:[/bold] {result.adherence_rate:.1%}",
            f"[bold]Days Logged:[/bold] {result.days_logged_pct:.1%}",
            f"[bold]Early Stop:[/bold] {result.early_stop}",
        ]
    )

    if result.late_backfill_excluded > 0:
        content_parts.append(
            f"[bold]Late Backfills Excluded:[/bold] {result.late_backfill_excluded}"
        )

    if result.sensitivity_excluding_partial:
        s = result.sensitivity_excluding_partial
        if s.difference is not None:
            content_parts.append(
                f"[bold]Sensitivity (no partial):[/bold] "
                f"diff={s.difference:+.2f}, CI=[{s.ci_lower:.2f}, {s.ci_upper:.2f}]"
            )

    content_parts.extend(
        [
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

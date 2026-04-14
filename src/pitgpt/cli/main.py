import asyncio
import csv
import json
import sys
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pitgpt.core.analysis import analyze, validate_observations
from pitgpt.core.ingestion import IngestionInputError, ingest
from pitgpt.core.io import load_analysis_protocol, parse_observations_csv, read_text_file
from pitgpt.core.llm import LLMClient
from pitgpt.core.models import Adherence, Condition, Observation, YesNo
from pitgpt.core.schedule import generate_schedule, generate_seed
from pitgpt.core.settings import load_settings
from pitgpt.core.templates import TRIAL_TEMPLATES

app = typer.Typer(name="pitgpt", help="PitGPT — personal clinical trial machine")
benchmark_app = typer.Typer(name="benchmark", help="Run and report on benchmarks")
demo_app = typer.Typer(name="demo", help="Run bundled examples")
trial_app = typer.Typer(name="trial", help="Create and randomize trial files")
checkin_app = typer.Typer(name="checkin", help="Append observation check-ins safely")
app.add_typer(benchmark_app, name="benchmark")
app.add_typer(demo_app, name="demo")
app.add_typer(trial_app, name="trial")
app.add_typer(checkin_app, name="checkin")

console = Console()

FORMAT_OPTION = typer.Option("pretty", help="Output format: json, table, pretty")
_OBSERVATION_HEADERS = [
    "day_index",
    "date",
    "condition",
    "primary_score",
    "irritation",
    "adherence",
    "note",
    "is_backfill",
    "backfill_days",
]


def _detect_format(fmt: str) -> str:
    if fmt != "pretty":
        return fmt
    if not sys.stdout.isatty():
        return "json"
    return "pretty"


def _read_file_or_exit(path: str | Path) -> str:
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _protocol_duration_weeks(raw_protocol: dict) -> int:
    if "duration_weeks" in raw_protocol:
        return int(raw_protocol["duration_weeks"])
    if "planned_days" in raw_protocol:
        planned_days = int(raw_protocol["planned_days"])
        return max(1, (planned_days + 6) // 7)
    raise ValueError("protocol must include duration_weeks or planned_days")


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
    try:
        result = asyncio.run(ingest(query, documents, client, model_id))
    except (IngestionInputError, KeyError, ValueError, ValidationError) as e:
        console.print(f"[red]Invalid ingestion response: {e}[/red]")
        raise typer.Exit(1) from e

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


@app.command("validate")
def validate_command(
    protocol: str = typer.Option(..., "--protocol", "-p", help="Protocol JSON file"),
    observations: str | None = typer.Option(
        None, "--observations", "-o", help="Observations CSV file"
    ),
    format: str = FORMAT_OPTION,
):
    """Validate protocol and observation files without running analysis."""
    fmt = _detect_format(format)
    try:
        proto_data = load_analysis_protocol(protocol)
        obs_data = parse_observations_csv(_read_file_or_exit(observations)) if observations else []
    except FileNotFoundError as e:
        console.print(f"[red]File not found: {e.filename}[/red]")
        raise typer.Exit(1) from e
    except (json.JSONDecodeError, ValidationError) as e:
        console.print(f"[red]Invalid input: {e}[/red]")
        raise typer.Exit(1) from e

    warnings = validate_observations(obs_data, proto_data) if observations else []
    payload = {
        "ok": True,
        "planned_days": proto_data.planned_days,
        "block_length_days": proto_data.block_length_days,
        "observation_count": len(obs_data),
        "warnings": warnings,
    }
    if fmt == "json":
        console.print_json(json.dumps(payload))
        return

    if warnings:
        console.print("[yellow]Validation completed with warnings:[/yellow]")
        for warning in warnings:
            console.print(f"  - {warning}")
    else:
        console.print("[green]Validation passed.[/green]")


@demo_app.command("analyze")
def demo_analyze_command(format: str = FORMAT_OPTION):
    """Analyze the bundled example trial. Works without an API key."""
    fmt = _detect_format(format)
    root = _repo_root()
    protocol = load_analysis_protocol(root / "examples" / "protocol.json")
    observations = parse_observations_csv(
        _read_file_or_exit(root / "examples" / "observations.csv")
    )
    result = analyze(protocol, observations)
    if fmt == "json":
        console.print_json(result.model_dump_json())
    else:
        _print_result_card(result)


@trial_app.command("init")
def trial_init_command(
    output_dir: str = typer.Option("pitgpt-trial", "--output-dir", "-o", help="Directory to write"),
    template_id: str = typer.Option("custom-ab", "--template", "-t", help="Template ID"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
):
    """Create protocol and observation template files for a new local trial."""
    template = next((item for item in TRIAL_TEMPLATES if item.id == template_id), None)
    if template is None:
        valid = ", ".join(item.id for item in TRIAL_TEMPLATES)
        console.print(f"[red]Unknown template '{template_id}'. Valid templates: {valid}[/red]")
        raise typer.Exit(1)

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    protocol_path = target / "protocol.json"
    observations_path = target / "observations.csv"
    schedule_path = target / "schedule.json"
    for path in (protocol_path, observations_path, schedule_path):
        if path.exists() and not force:
            console.print(f"[red]{path} already exists. Pass --force to overwrite.[/red]")
            raise typer.Exit(1)

    protocol_payload = {
        "planned_days": template.protocol.duration_weeks * 7,
        "block_length_days": template.protocol.block_length_days,
        "minimum_meaningful_difference": 0.5,
    }
    seed = generate_seed()
    schedule = generate_schedule(
        template.protocol.duration_weeks,
        template.protocol.block_length_days,
        seed,
    )
    protocol_path.write_text(json.dumps(protocol_payload, indent=2) + "\n")
    observations_path.write_text(",".join(_OBSERVATION_HEADERS) + "\n")
    schedule_path.write_text(
        json.dumps(
            {"seed": seed, "assignments": [item.model_dump(mode="json") for item in schedule]},
            indent=2,
        )
        + "\n"
    )
    console.print(f"[green]Trial files written to {target}[/green]")
    console.print(f"Condition A: {template.condition_a_placeholder}")
    console.print(f"Condition B: {template.condition_b_placeholder}")


@trial_app.command("randomize")
def trial_randomize_command(
    protocol: str = typer.Option(..., "--protocol", "-p", help="Protocol JSON file"),
    seed: int | None = typer.Option(None, "--seed", "-s", help="Deterministic seed"),
    format: str = FORMAT_OPTION,
):
    """Generate a deterministic period schedule from protocol fields."""
    fmt = _detect_format(format)
    try:
        raw_protocol = json.loads(_read_file_or_exit(protocol))
        duration_weeks = _protocol_duration_weeks(raw_protocol)
        block_length_days = int(raw_protocol.get("block_length_days", 7))
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        console.print(f"[red]Invalid protocol file: {e}[/red]")
        raise typer.Exit(1) from e

    selected_seed = seed if seed is not None else generate_seed()
    schedule = generate_schedule(duration_weeks, block_length_days, selected_seed)
    payload = {
        "seed": selected_seed,
        "duration_weeks": duration_weeks,
        "block_length_days": block_length_days,
        "assignments": [item.model_dump(mode="json") for item in schedule],
    }
    if fmt == "json":
        console.print_json(json.dumps(payload))
        return

    table = Table(title=f"Schedule — seed {selected_seed}")
    table.add_column("Period", justify="right")
    table.add_column("Pair", justify="right")
    table.add_column("Days")
    table.add_column("Condition")
    for item in schedule:
        table.add_row(
            str(item.period_index + 1),
            str(item.pair_index + 1),
            f"{item.start_day}-{item.end_day}",
            item.condition.value,
        )
    console.print(table)


@checkin_app.command("add")
def checkin_add_command(
    observations: str = typer.Option(..., "--observations", "-o", help="Observations CSV file"),
    day_index: int = typer.Option(..., "--day", "-d", min=1, help="Trial day index"),
    condition: Annotated[Condition | None, typer.Option("--condition", "-c", help="A or B")] = None,
    score: float = typer.Option(..., "--score", "-s", min=0, max=10, help="0-10 outcome score"),
    observation_date: str | None = typer.Option(None, "--date", help="YYYY-MM-DD date"),
    irritation: Annotated[YesNo, typer.Option("--irritation", help="yes or no")] = YesNo.NO,
    adherence: Annotated[
        Adherence,
        typer.Option("--adherence", help="yes, no, or partial"),
    ] = Adherence.YES,
    note: str = typer.Option("", "--note", "-n", help="Optional note"),
    backfill_days: float | None = typer.Option(
        None, "--backfill-days", help="Days since observation"
    ),
    force: bool = typer.Option(False, "--force", help="Append even when day/date already exists"),
):
    """Append one observation row while guarding duplicate day/date entries."""
    if condition is None:
        console.print("[red]--condition is required.[/red]")
        raise typer.Exit(1)

    path = Path(observations)
    existing = parse_observations_csv(path.read_text()) if path.exists() else []
    obs_date = observation_date or date.today().isoformat()
    if not force and any(item.day_index == day_index or item.date == obs_date for item in existing):
        console.print(
            "[red]That day or date already has an observation. Pass --force to append anyway.[/red]"
        )
        raise typer.Exit(1)

    observation = Observation(
        day_index=day_index,
        date=obs_date,
        condition=condition,
        primary_score=score,
        irritation=irritation,
        adherence=adherence,
        note=note,
        is_backfill=YesNo.YES if backfill_days and backfill_days > 0 else YesNo.NO,
        backfill_days=backfill_days,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_OBSERVATION_HEADERS)
        if write_header:
            writer.writeheader()
        writer.writerow(observation.model_dump(mode="json"))
    console.print(f"[green]Observation appended to {path}[/green]")


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
        f"[bold]Risk Level:[/bold] {result.risk_level.value}",
        f"[bold]Evidence Quality:[/bold] {result.evidence_quality.value}",
        f"[bold]Evidence Conflict:[/bold] {result.evidence_conflict}",
        f"[bold]Policy Version:[/bold] {result.policy_version or 'unknown'}",
        f"[bold]Model:[/bold] {result.model or 'unknown'}",
    ]
    if result.risk_rationale:
        content_parts.append(f"[bold]Risk Rationale:[/bold] {result.risk_rationale}")
    if result.clinician_note:
        content_parts.append(f"[bold]Clinician Note:[/bold] {result.clinician_note}")

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
        if p.clinician_note:
            content_parts.append(f"  Clinician Note: {p.clinician_note}")
        if p.suggested_confounders:
            content_parts.append(f"  Optional Context: {', '.join(p.suggested_confounders)}")

    if result.source_summaries:
        content_parts.extend(["", "[bold underline]Source Summaries[/bold underline]"])
        content_parts.extend(f"  - {item}" for item in result.source_summaries)

    if result.sources:
        content_parts.extend(["", "[bold underline]Sources[/bold underline]"])
        content_parts.extend(
            f"  - {source.title or source.source_id}: {source.summary or source.rationale}"
            for source in result.sources
        )

    if result.claimed_outcomes:
        content_parts.extend(["", "[bold underline]Claimed Outcomes[/bold underline]"])
        content_parts.extend(f"  - {item}" for item in result.claimed_outcomes)

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
        f"[bold]Analysis Method:[/bold] {result.analysis_method.value}",
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
        content_parts.append(
            f"[bold]Minimum Meaningful Difference:[/bold] "
            f"{result.minimum_meaningful_difference:.2f} "
            f"({'met' if result.meets_minimum_meaningful_effect else 'not met'})"
        )

    if result.paired_block and result.paired_block.difference is not None:
        p = result.paired_block
        content_parts.append(
            f"[bold]Paired Blocks:[/bold] diff={p.difference:+.2f}, pairs={p.n_pairs}"
        )

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

    if result.data_warnings:
        content_parts.append("[bold]Data Warnings:[/bold]")
        content_parts.extend(f"  - {warning}" for warning in result.data_warnings)

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

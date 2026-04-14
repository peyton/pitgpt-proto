import asyncio
import csv
import io
import json
import math
import sys
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pitgpt.core.analysis import analyze
from pitgpt.core.ingestion import IngestionInputError, ingest
from pitgpt.core.io import load_analysis_protocol, parse_observations_csv, read_text_file
from pitgpt.core.llm import LLMClient
from pitgpt.core.models import (
    Adherence,
    AnalysisProtocol,
    Condition,
    Observation,
    ProtocolAmendment,
    ResultCard,
    TrialBundle,
    TrialBundleManifest,
    YesNo,
)
from pitgpt.core.schedule import generate_schedule, generate_seed
from pitgpt.core.settings import load_settings
from pitgpt.core.templates import TRIAL_TEMPLATES
from pitgpt.core.validation import validate_trial

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
    "assigned_condition",
    "actual_condition",
    "primary_score",
    "irritation",
    "adherence",
    "adherence_reason",
    "note",
    "is_backfill",
    "backfill_days",
    "adverse_event_severity",
    "adverse_event_description",
    "secondary_scores",
    "recorded_at",
    "timezone",
    "planned_checkin_time",
    "minutes_from_planned_checkin",
    "exposure_start_at",
    "exposure_end_at",
    "measurement_timing",
    "deviation_codes",
    "confounders",
    "rescue_action",
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


def _read_protocol_observations(
    protocol: str | Path,
    observations: str | Path,
) -> tuple[AnalysisProtocol, list[Observation]]:
    proto_data = load_analysis_protocol(protocol)
    obs_data = parse_observations_csv(_read_file_or_exit(observations))
    return proto_data, obs_data


def _json_or_text(value: Any) -> str:
    return json.dumps(value) if not isinstance(value, str) else value


@app.command("ingest")
def ingest_command(
    query: str = typer.Option(..., "--query", "-q", help="Natural language question"),
    doc: list[str] = typer.Option(  # noqa: B008
        [], "--doc", "-d", help="Document file paths"
    ),
    model: str | None = typer.Option(None, "--model", "-m", help="Model identifier"),
    no_limit: bool = typer.Option(
        False, "--no-limit", help="Skip configured source character limits"
    ),
    format: str = FORMAT_OPTION,
):
    """Run research ingestion and produce a protocol or safety decision."""
    fmt = _detect_format(format)
    model_id = _get_model(model)
    documents = [_read_file_or_exit(d) for d in doc]
    client = _get_client(model_id)
    try:
        limit = 10**12 if no_limit else None
        result = asyncio.run(ingest(query, documents, client, model_id, limit, limit))
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
        obs_data = (
            parse_observations_csv(_read_file_or_exit(observations), strict=True)
            if observations
            else []
        )
    except FileNotFoundError as e:
        console.print(f"[red]File not found: {e.filename}[/red]")
        raise typer.Exit(1) from e
    except (json.JSONDecodeError, ValidationError) as e:
        console.print(f"[red]Invalid input: {e}[/red]")
        raise typer.Exit(1) from e

    payload = validate_trial(proto_data, obs_data).model_dump(mode="json")
    if fmt == "json":
        console.print_json(json.dumps(payload))
        return

    if payload["errors"]:
        console.print("[red]Validation failed:[/red]")
        for error in payload["errors"]:
            console.print(f"  - {error}")
        raise typer.Exit(1)
    if payload["warnings"]:
        console.print("[yellow]Validation completed with warnings:[/yellow]")
        for warning in payload["warnings"]:
            console.print(f"  - {warning}")
    else:
        console.print("[green]Validation passed.[/green]")


@app.command("brief")
def brief_command(
    protocol: str = typer.Option(..., "--protocol", "-p", help="Protocol JSON file"),
    observations: str = typer.Option(..., "--observations", "-o", help="Observations CSV file"),
    format: str = FORMAT_OPTION,
):
    """Print a compact analysis brief for a trial."""
    fmt = _detect_format(format)
    proto_data, obs_data = _read_protocol_observations(protocol, observations)
    result = analyze(proto_data, obs_data)
    payload = {
        "summary": result.summary,
        "quality_grade": result.quality_grade.value,
        "verdict": result.verdict,
        "adherence_rate": result.adherence_rate,
        "days_logged_pct": result.days_logged_pct,
        "adverse_event_count": result.adverse_event_count,
        "caveats": result.caveats,
    }
    if fmt == "json":
        console.print_json(json.dumps(payload))
        return
    console.print(Panel(result.summary, title=f"Brief — Grade {result.quality_grade.value}"))
    console.print(f"Verdict: {result.verdict}")
    console.print(
        f"Adherence: {result.adherence_rate:.1%}; days logged: {result.days_logged_pct:.1%}"
    )
    if result.adverse_event_count:
        console.print(f"Discomfort logged: {result.adverse_event_count} day(s)")


@app.command("power")
def power_command(
    effect: float = typer.Option(0.5, "--effect", "-e", min=0.01, help="Meaningful difference"),
    sigma: float = typer.Option(1.5, "--sigma", "-s", min=0.01, help="Expected SD"),
    alpha: float = typer.Option(0.05, "--alpha", min=0.001, max=0.5, help="Two-sided alpha"),
    power: float = typer.Option(0.8, "--power", min=0.5, max=0.99, help="Target power"),
    format: str = FORMAT_OPTION,
):
    """Estimate per-condition observations needed for a two-condition comparison."""
    fmt = _detect_format(format)
    z_alpha = _normal_quantile(1 - alpha / 2)
    z_power = _normal_quantile(power)
    per_condition = math.ceil(2 * ((z_alpha + z_power) * sigma / effect) ** 2)
    payload = {
        "effect": effect,
        "sigma": sigma,
        "alpha": alpha,
        "power": power,
        "observations_per_condition": per_condition,
        "total_observations": per_condition * 2,
    }
    if fmt == "json":
        console.print_json(json.dumps(payload))
        return
    console.print(
        f"Estimated observations: {per_condition} per condition ({per_condition * 2} total)."
    )


@app.command("doctor")
def doctor_command(format: str = FORMAT_OPTION):
    """Check local PitGPT configuration and common prerequisites."""
    fmt = _detect_format(format)
    settings = load_settings()
    checks = [
        {"name": "OPENROUTER_API_KEY", "ok": bool(settings.openrouter_api_key)},
        {
            "name": "Default model",
            "ok": bool(settings.default_model),
            "detail": settings.default_model,
        },
        {
            "name": "API token optional",
            "ok": True,
            "detail": "set" if settings.api_token else "not set",
        },
        {
            "name": "LLM cache optional",
            "ok": True,
            "detail": "enabled" if settings.llm_cache_enabled else "disabled",
        },
        {
            "name": "Document limits",
            "ok": True,
            "detail": _document_limit_detail(
                settings.max_document_chars,
                settings.max_total_document_chars,
            ),
        },
    ]
    payload = {
        "ok": all(item["ok"] for item in checks if item["name"] != "OPENROUTER_API_KEY"),
        "checks": checks,
    }
    if fmt == "json":
        console.print_json(json.dumps(payload))
        return
    for item in checks:
        marker = "[green]ok[/green]" if item["ok"] else "[yellow]missing[/yellow]"
        detail = f" — {item.get('detail', '')}" if item.get("detail") else ""
        console.print(f"{marker} {item['name']}{detail}")


def _document_limit_detail(per_document: int | None, total: int | None) -> str:
    if per_document is None and total is None:
        return "unlimited"
    per_doc_label = "unlimited" if per_document is None else f"{per_document} chars"
    total_label = "unlimited" if total is None else f"{total} chars"
    return f"{per_doc_label}/{total_label}"


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


@trial_app.command("status")
def trial_status_command(
    protocol: str = typer.Option(..., "--protocol", "-p", help="Protocol JSON file"),
    observations: str = typer.Option(..., "--observations", "-o", help="Observations CSV file"),
    format: str = FORMAT_OPTION,
):
    """Show current day, adherence, and validation status for a local trial."""
    fmt = _detect_format(format)
    proto_data, obs_data = _read_protocol_observations(protocol, observations)
    report = validate_trial(proto_data, obs_data)
    max_day = max((item.day_index for item in obs_data), default=0)
    adherence_yes = sum(1 for item in obs_data if item.adherence == Adherence.YES)
    payload = {
        "current_day": max_day,
        "planned_days": proto_data.planned_days,
        "observations": len(obs_data),
        "adherence_rate_observed": adherence_yes / len(obs_data) if obs_data else 0,
        "validation": report.model_dump(mode="json"),
    }
    if fmt == "json":
        console.print_json(json.dumps(payload))
        return
    console.print(f"Day {max_day} of {proto_data.planned_days}; {len(obs_data)} observation(s).")
    console.print(f"Observed adherence: {payload['adherence_rate_observed']:.1%}")
    if report.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in report.warnings:
            console.print(f"  - {warning}")


@trial_app.command("export")
def trial_export_command(
    protocol: str = typer.Option(..., "--protocol", "-p", help="Protocol JSON file"),
    observations: str = typer.Option(..., "--observations", "-o", help="Observations CSV file"),
    output: str = typer.Option("pitgpt-trial-bundle.json", "--output", help="Output .json or .zip"),
    include_result: bool = typer.Option(
        True, "--include-result/--no-result", help="Include analysis result"
    ),
):
    """Export protocol, observations, and optional result as one bundle."""
    proto_data, obs_data = _read_protocol_observations(protocol, observations)
    result = analyze(proto_data, obs_data) if include_result else None
    exported_at = datetime.now(UTC).isoformat()
    bundle = TrialBundle(
        manifest=TrialBundleManifest(exported_at=exported_at),
        protocol=proto_data,
        observations=obs_data,
        result=result,
    )
    output_path = Path(output)
    if output_path.suffix == ".zip":
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", bundle.manifest.model_dump_json(indent=2))
            archive.writestr("protocol.json", bundle.protocol.model_dump_json(indent=2))
            archive.writestr("observations.csv", _observations_to_csv(obs_data))
            if result:
                archive.writestr("result.json", result.model_dump_json(indent=2))
    else:
        output_path.write_text(bundle.model_dump_json(indent=2) + "\n")
    console.print(f"[green]Bundle written to {output_path}[/green]")


@trial_app.command("import")
def trial_import_command(
    bundle: str = typer.Option(..., "--bundle", "-b", help="Bundle .json or .zip"),
    output_dir: str = typer.Option("pitgpt-trial-import", "--output-dir", "-o"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
):
    """Import a bundle into protocol, observations, and result files."""
    source = Path(bundle)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    protocol_path = target / "protocol.json"
    observations_path = target / "observations.csv"
    result_path = target / "result.json"
    for path in (protocol_path, observations_path, result_path):
        if path.exists() and not force:
            console.print(f"[red]{path} already exists. Pass --force to overwrite.[/red]")
            raise typer.Exit(1)

    if source.suffix == ".zip":
        with zipfile.ZipFile(source) as archive:
            protocol_text = archive.read("protocol.json").decode()
            observations_text = archive.read("observations.csv").decode()
            result_text = (
                archive.read("result.json").decode() if "result.json" in archive.namelist() else ""
            )
            parsed_protocol = AnalysisProtocol.model_validate(json.loads(protocol_text))
            parsed_observations = parse_observations_csv(observations_text, strict=True)
            parsed_result = (
                ResultCard.model_validate(json.loads(result_text)) if result_text else None
            )
            protocol_path.write_text(parsed_protocol.model_dump_json(indent=2) + "\n")
            observations_path.write_text(_observations_to_csv(parsed_observations))
            if parsed_result is not None:
                result_path.write_text(parsed_result.model_dump_json(indent=2) + "\n")
    else:
        parsed = TrialBundle.model_validate(json.loads(source.read_text()))
        protocol_path.write_text(parsed.protocol.model_dump_json(indent=2) + "\n")
        observations_path.write_text(_observations_to_csv(parsed.observations))
        if parsed.result:
            result_path.write_text(parsed.result.model_dump_json(indent=2) + "\n")
    console.print(f"[green]Bundle imported to {target}[/green]")


@trial_app.command("amend")
def trial_amend_command(
    protocol: str = typer.Option(..., "--protocol", "-p", help="Protocol JSON file to update"),
    field: str = typer.Option(..., "--field", help="Protocol field being amended"),
    value: str = typer.Option(..., "--value", help="New value as text"),
    reason: str = typer.Option(..., "--reason", help="Why the amendment was made"),
):
    """Append a protocol amendment record without changing analysis history."""
    path = Path(protocol)
    raw = json.loads(path.read_text())
    amendments = raw.setdefault("amendments", [])
    old_raw = raw.get(field, "")
    old_value = _json_or_text(old_raw)
    new_raw = _parse_typed_value(value)
    raw[field] = new_raw
    amendments.append(
        ProtocolAmendment(
            date=date.today().isoformat(),
            field=field,
            old_value=old_value,
            new_value=_json_or_text(new_raw),
            reason=reason,
        ).model_dump(mode="json")
    )
    path.write_text(json.dumps(raw, indent=2) + "\n")
    console.print(f"[green]Amendment added to {path}[/green]")


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
        row = observation.model_dump(mode="json")
        row["secondary_scores"] = json.dumps(row.get("secondary_scores", {}), sort_keys=True)
        row["deviation_codes"] = json.dumps(row.get("deviation_codes", []), sort_keys=True)
        row["confounders"] = json.dumps(row.get("confounders", {}), sort_keys=True)
        writer.writerow({header: row.get(header, "") for header in _OBSERVATION_HEADERS})
    console.print(f"[green]Observation appended to {path}[/green]")


def _observations_to_csv(observations: list[Observation]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_OBSERVATION_HEADERS)
    writer.writeheader()
    for observation in observations:
        row = observation.model_dump(mode="json")
        row["secondary_scores"] = json.dumps(row.get("secondary_scores", {}), sort_keys=True)
        row["deviation_codes"] = json.dumps(row.get("deviation_codes", []), sort_keys=True)
        row["confounders"] = json.dumps(row.get("confounders", {}), sort_keys=True)
        writer.writerow({header: row.get(header, "") for header in _OBSERVATION_HEADERS})
    return output.getvalue()


def _parse_typed_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _normal_quantile(p: float) -> float:
    # Peter J. Acklam's approximation, accurate enough for planning estimates.
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        numerator = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q) + c[5]
        denominator = ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q) + 1
        return numerator / denominator
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        numerator = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q) + c[5]
        denominator = ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q) + 1
        return -numerator / denominator
    q = p - 0.5
    r = q * q
    numerator = ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r) + a[5]) * q
    denominator = (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r) + 1
    return numerator / denominator


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

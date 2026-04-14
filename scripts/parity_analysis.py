from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from pitgpt.core.analysis import analyze
from pitgpt.core.io import parse_observations_csv
from pitgpt.core.models import AnalysisProtocol

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "benchmarks" / "analysis_fixtures"

PARITY_FIELDS = (
    "quality_grade",
    "verdict",
    "analysis_method",
    "difference",
    "ci_lower",
    "ci_upper",
    "n_used_a",
    "n_used_b",
    "adherence_rate",
    "days_logged_pct",
    "late_backfill_excluded",
    "randomization_p_value",
)

PAIRED_FIELDS = (
    "difference",
    "ci_lower",
    "ci_upper",
    "n_pairs",
    "randomization_p_value",
)


def main() -> None:
    failures: list[str] = []
    case_ids = sorted(
        path.name.removesuffix("_protocol.json") for path in FIXTURES_DIR.glob("*_protocol.json")
    )
    for case_id in case_ids:
        protocol_path = FIXTURES_DIR / f"{case_id}_protocol.json"
        observations_path = FIXTURES_DIR / f"{case_id}_observations.csv"
        python_result = python_analysis(protocol_path, observations_path)
        rust_result = rust_analysis(protocol_path, observations_path)
        failures.extend(compare_case(case_id, python_result, rust_result))

    if failures:
        joined = "\n".join(f"  - {failure}" for failure in failures)
        raise SystemExit(f"Python/Rust analysis parity failed:\n{joined}")

    print(f"Python/Rust analysis parity passed for {len(case_ids)} case(s).")


def python_analysis(protocol_path: Path, observations_path: Path) -> dict[str, Any]:
    protocol = AnalysisProtocol.model_validate(json.loads(protocol_path.read_text()))
    observations = parse_observations_csv(observations_path.read_text())
    return analyze(protocol, observations).model_dump(mode="json")


def rust_analysis(protocol_path: Path, observations_path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            "./bin/mise",
            "exec",
            "--",
            "cargo",
            "run",
            "--quiet",
            "--manifest-path",
            "src-tauri/Cargo.toml",
            "--bin",
            "analysis_parity",
            "--",
            str(protocol_path),
            str(observations_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def compare_case(
    case_id: str,
    python_result: dict[str, Any],
    rust_result: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    for field in PARITY_FIELDS:
        failures.extend(
            compare_value(case_id, field, python_result.get(field), rust_result.get(field))
        )

    python_paired = python_result.get("paired_block")
    rust_paired = rust_result.get("paired_block")
    if python_paired is None or rust_paired is None:
        if python_paired != rust_paired:
            failures.append(
                f"{case_id}.paired_block: Python={python_paired!r} Rust={rust_paired!r}"
            )
        return failures

    for field in PAIRED_FIELDS:
        failures.extend(
            compare_value(
                case_id,
                f"paired_block.{field}",
                python_paired.get(field),
                rust_paired.get(field),
            )
        )
    return failures


def compare_value(case_id: str, field: str, python_value: Any, rust_value: Any) -> list[str]:
    if isinstance(python_value, float) or isinstance(rust_value, float):
        if python_value is None or rust_value is None:
            if python_value == rust_value:
                return []
            return [f"{case_id}.{field}: Python={python_value!r} Rust={rust_value!r}"]
        if abs(float(python_value) - float(rust_value)) <= 0.011:
            return []
        return [f"{case_id}.{field}: Python={python_value!r} Rust={rust_value!r}"]

    if python_value == rust_value:
        return []
    return [f"{case_id}.{field}: Python={python_value!r} Rust={rust_value!r}"]


if __name__ == "__main__":
    main()

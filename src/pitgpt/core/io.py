import csv
import io
import json
from pathlib import Path
from typing import Any

from pitgpt.core.models import AnalysisProtocol, Observation


def read_text_file(path: str | Path) -> str:
    return Path(path).read_text()


def load_json_file(path: str | Path) -> Any:
    return json.loads(read_text_file(path))


def load_analysis_protocol(path: str | Path) -> AnalysisProtocol:
    return AnalysisProtocol.model_validate(load_json_file(path))


def parse_observations_csv(content: str) -> list[Observation]:
    if not content.strip():
        return []

    observations: list[Observation] = []
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        normalized = _normalize_observation_row(row)
        if not normalized:
            continue
        observations.append(Observation.model_validate(normalized))
    return observations


def parse_observations_csv_file(path: str | Path) -> list[Observation]:
    return parse_observations_csv(read_text_file(path))


def _normalize_observation_row(row: dict[str, str | None]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        if key is None:
            continue
        clean_key = key.strip()
        if not clean_key:
            continue
        parsed_value: Any = value.strip() if value is not None else None
        if parsed_value == "" and clean_key in _EMPTY_AS_NONE_FIELDS:
            parsed_value = None
        elif parsed_value == "" and clean_key in _EMPTY_AS_DEFAULT_FIELDS:
            continue
        elif clean_key == "secondary_scores":
            parsed_value = _parse_secondary_scores(parsed_value)
        normalized[clean_key] = parsed_value
    return normalized


def _parse_secondary_scores(value: str | None) -> dict[str, float]:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("secondary_scores must be a JSON object")
    scores: dict[str, float] = {}
    for key, score in parsed.items():
        if isinstance(key, str) and isinstance(score, int | float):
            scores[key] = float(score)
    return scores


_EMPTY_AS_NONE_FIELDS = {
    "primary_score",
    "backfill_days",
    "adverse_event_severity",
}

_EMPTY_AS_DEFAULT_FIELDS = {
    "irritation",
    "adherence",
    "adherence_reason",
    "note",
    "is_backfill",
    "adverse_event_description",
    "secondary_scores",
}

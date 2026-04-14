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


def _normalize_observation_row(row: dict[str, str | None]) -> dict[str, str | None]:
    normalized: dict[str, str | None] = {}
    for key, value in row.items():
        if key is None:
            continue
        clean_key = key.strip()
        if not clean_key:
            continue
        clean_value = value.strip() if value is not None else None
        if clean_value == "" and clean_key in _EMPTY_AS_NONE_FIELDS:
            clean_value = None
        elif clean_value == "" and clean_key in _EMPTY_AS_DEFAULT_FIELDS:
            continue
        normalized[clean_key] = clean_value
    return normalized


_EMPTY_AS_NONE_FIELDS = {
    "primary_score",
    "backfill_days",
}

_EMPTY_AS_DEFAULT_FIELDS = {
    "irritation",
    "adherence",
    "note",
    "is_backfill",
}

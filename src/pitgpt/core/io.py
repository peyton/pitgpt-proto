import csv
import io
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pitgpt.core.models import AnalysisProtocol, Observation


def read_text_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_json_file(path: str | Path) -> Any:
    return json.loads(read_text_file(path))


def load_analysis_protocol(path: str | Path) -> AnalysisProtocol:
    return AnalysisProtocol.model_validate(load_json_file(path))


def parse_observations_csv(content: str, strict: bool = False) -> list[Observation]:
    if not content.strip():
        return []

    observations: list[Observation] = []
    reader = csv.DictReader(io.StringIO(content))
    if strict:
        _validate_headers(reader.fieldnames or [])
    for row in reader:
        normalized = _normalize_observation_row(row)
        if not normalized:
            continue
        observations.append(Observation.model_validate(normalized))
    if strict:
        _validate_strict_rows(observations)
    return observations


def parse_observations_csv_file(path: str | Path, strict: bool = False) -> list[Observation]:
    return parse_observations_csv(read_text_file(path), strict=strict)


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
        elif clean_key == "confounders":
            parsed_value = _parse_string_dict(parsed_value)
        elif clean_key == "deviation_codes":
            parsed_value = _parse_string_list(parsed_value)
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
        if not isinstance(score, int | float):
            raise ValueError(f"secondary_scores.{key} must be numeric")
        scores[str(key)] = float(score)
    return scores


def _parse_string_dict(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("confounders must be a JSON object")
    return {
        str(key).strip(): str(item).strip()
        for key, item in parsed.items()
        if str(key).strip() and str(item).strip()
    }


def _parse_string_list(value: str | None) -> list[str]:
    if not value:
        return []
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError("deviation_codes must be a JSON array")
    return [str(item).strip() for item in parsed if str(item).strip()]


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
    "confounders",
    "deviation_codes",
}

_OBSERVATION_HEADERS = {
    "observation_id",
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
}

_REQUIRED_HEADERS = {"day_index", "date", "condition"}


def _validate_headers(fieldnames: Sequence[str]) -> None:
    headers = {field.strip() for field in fieldnames if field and field.strip()}
    missing = sorted(_REQUIRED_HEADERS.difference(headers))
    if missing:
        raise ValueError(f"Observations CSV missing required column(s): {', '.join(missing)}.")
    unknown = sorted(headers.difference(_OBSERVATION_HEADERS))
    if unknown:
        raise ValueError(f"Observations CSV has unknown column(s): {', '.join(unknown)}.")


def _validate_strict_rows(observations: list[Observation]) -> None:
    days = [observation.day_index for observation in observations]
    dates = [observation.date for observation in observations if observation.date]
    duplicate_days = sorted(day for day, count in Counter(days).items() if count > 1)
    duplicate_dates = sorted(date for date, count in Counter(dates).items() if count > 1)
    errors = []
    if duplicate_days:
        errors.append(f"duplicate day_index value(s): {', '.join(map(str, duplicate_days))}")
    if duplicate_dates:
        errors.append(f"duplicate date value(s): {', '.join(duplicate_dates)}")
    if days != sorted(days):
        errors.append("day_index values are not sorted")
    if dates != sorted(dates):
        errors.append("date values are not sorted")
    if errors:
        raise ValueError("Invalid observations CSV: " + "; ".join(errors) + ".")

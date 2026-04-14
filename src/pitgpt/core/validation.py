from pydantic import ValidationError

from pitgpt.core.analysis import validate_observations
from pitgpt.core.models import AnalysisProtocol, Observation, ValidationReport


def validate_trial(
    protocol: AnalysisProtocol,
    observations: list[Observation],
) -> ValidationReport:
    warnings = validate_observations(observations, protocol)
    errors: list[str] = []
    if observations:
        max_day = max(observation.day_index for observation in observations)
        if max_day > protocol.planned_days:
            warnings.append(
                f"Observation day_index {max_day} exceeds planned_days {protocol.planned_days}."
            )

    return ValidationReport(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        observation_count=len(observations),
        planned_days=protocol.planned_days,
        block_length_days=protocol.block_length_days,
    )


def validation_report_from_error(error: ValidationError | ValueError) -> ValidationReport:
    return ValidationReport(valid=False, errors=[str(error)])

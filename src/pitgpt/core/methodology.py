import hashlib
import json
from typing import Any

from pydantic import BaseModel

from pitgpt.core.models import (
    AnalysisPlan,
    AnalysisProtocol,
    MethodsAppendix,
    Observation,
    TrialLock,
)

METHOD_VERSION = "2026-04-14-paired-primary-v1"


def canonical_json(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", exclude_none=True)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def build_trial_lock(
    protocol: AnalysisProtocol,
    observations: list[Observation],
    locked_at: str = "",
) -> TrialLock:
    analysis_plan = protocol.analysis_plan
    estimand = analysis_plan.estimand
    return TrialLock(
        protocol_hash=sha256_digest(protocol),
        analysis_plan_hash=sha256_digest(analysis_plan),
        estimand_hash=sha256_digest(estimand),
        schedule_hash=sha256_digest(
            {
                "planned_days": protocol.planned_days,
                "block_length_days": protocol.block_length_days,
                "observed_days": [observation.day_index for observation in observations],
            }
        ),
        locked_at=locked_at,
    )


def build_methods_appendix(
    protocol: AnalysisProtocol,
    observations: list[Observation],
    sensitivity_methods: list[str],
    row_exclusion_reasons: list[str],
) -> MethodsAppendix:
    analysis_plan = protocol.analysis_plan
    return MethodsAppendix(
        method_version=METHOD_VERSION,
        estimand=analysis_plan.estimand,
        analysis_plan=AnalysisPlan.model_validate(
            {
                **analysis_plan.model_dump(mode="json"),
                "method_version": METHOD_VERSION,
            }
        ),
        trial_lock=build_trial_lock(protocol, observations),
        input_hashes={
            "protocol": sha256_digest(protocol),
            "observations": sha256_digest([obs.model_dump(mode="json") for obs in observations]),
        },
        sensitivity_methods=sensitivity_methods,
        row_exclusion_reasons=row_exclusion_reasons,
        software_versions={"pitgpt": "0.1.0", "method": METHOD_VERSION},
        pre_specified=analysis_plan.pre_specified,
    )

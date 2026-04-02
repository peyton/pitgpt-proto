from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class SafetyTier(StrEnum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class EvidenceQuality(StrEnum):
    NOVEL = "novel"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class IngestionDecision(StrEnum):
    GENERATE_PROTOCOL = "generate_protocol"
    GENERATE_PROTOCOL_WITH_RESTRICTIONS = "generate_protocol_with_restrictions"
    MANUAL_REVIEW_BEFORE_PROTOCOL = "manual_review_before_protocol"
    BLOCK = "block"


class QualityGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class Protocol(BaseModel):
    template: str | None = None
    duration_weeks: int
    block_length_days: int
    cadence: str
    washout: str
    primary_outcome_question: str
    screening: str = ""
    warnings: str = ""


class IngestionResult(BaseModel):
    decision: IngestionDecision
    safety_tier: SafetyTier
    evidence_quality: EvidenceQuality
    evidence_conflict: bool = False
    protocol: Protocol | None = None
    block_reason: str | None = None
    user_message: str


class Observation(BaseModel):
    day_index: int
    date: str
    condition: str
    primary_score: float | None = None
    irritation: str = "no"
    adherence: str = "yes"
    note: str = ""
    is_backfill: str = "no"
    backfill_days: float | None = None


class BlockBreakdown(BaseModel):
    block_index: int
    condition: str
    mean: float
    n: int


class SensitivityResult(BaseModel):
    difference: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    n_used_a: int = 0
    n_used_b: int = 0


Verdict = Literal["favors_a", "favors_b", "inconclusive", "insufficient_data"]


class ResultCard(BaseModel):
    quality_grade: QualityGrade
    verdict: Verdict = "insufficient_data"
    mean_a: float | None = None
    mean_b: float | None = None
    difference: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    cohens_d: float | None = None
    n_used_a: int = 0
    n_used_b: int = 0
    adherence_rate: float = 0.0
    days_logged_pct: float = 0.0
    early_stop: bool = False
    late_backfill_excluded: int = 0
    block_breakdown: list[BlockBreakdown] = []
    sensitivity_excluding_partial: SensitivityResult | None = None
    planned_days_defaulted: bool = False
    summary: str = ""
    caveats: str = ""

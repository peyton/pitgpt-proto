from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SafetyTier(StrEnum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class RiskLevel(StrEnum):
    LOW = "low"
    CONDITION_ADJACENT_LOW = "condition_adjacent_low"
    MODERATE = "moderate"
    HIGH = "high"
    CLINICIAN_REVIEW = "clinician_review"


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


class Condition(StrEnum):
    A = "A"
    B = "B"


class YesNo(StrEnum):
    YES = "yes"
    NO = "no"


class Adherence(StrEnum):
    YES = "yes"
    PARTIAL = "partial"
    NO = "no"


class AnalysisMethod(StrEnum):
    WELCH = "welch"
    PAIRED_BLOCKS = "paired_blocks"
    INSUFFICIENT_DATA = "insufficient_data"


class ResearchSource(BaseModel):
    source_id: str = ""
    source_type: str = "text"
    title: str = ""
    locator: str = ""
    evidence_quality: EvidenceQuality | None = None
    summary: str = ""
    rationale: str = ""


class ExtractedClaim(BaseModel):
    intervention: str = ""
    comparator: str = ""
    routine: str = ""
    outcome: str = ""
    population: str = ""
    duration: str = ""
    timing: str = ""
    effect_size: str = ""
    source_refs: list[str] = Field(default_factory=list)


class SuitabilityScore(BaseModel):
    dimension: str
    score: int = Field(ge=1, le=5)
    rationale: str = ""


class Protocol(BaseModel):
    template: str | None = None
    duration_weeks: int = Field(gt=0)
    block_length_days: int = Field(gt=0)
    cadence: str
    washout: str
    primary_outcome_question: str
    screening: str = ""
    warnings: str = ""
    outcome_anchor_low: str = ""
    outcome_anchor_mid: str = ""
    outcome_anchor_high: str = ""
    condition_a_instructions: str = ""
    condition_b_instructions: str = ""
    suggested_confounders: list[str] = Field(default_factory=list)
    clinician_note: str = ""
    readiness_checklist: list[str] = Field(default_factory=list)


class AnalysisProtocol(BaseModel):
    planned_days: int = Field(default=42, gt=0)
    block_length_days: int = Field(default=7, gt=0)
    minimum_meaningful_difference: float = Field(default=0.5, ge=0)


class IngestionResult(BaseModel):
    decision: IngestionDecision
    safety_tier: SafetyTier
    evidence_quality: EvidenceQuality
    evidence_conflict: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    risk_rationale: str = ""
    clinician_note: str = ""
    protocol: Protocol | None = None
    block_reason: str | None = None
    user_message: str
    policy_version: str = ""
    model: str | None = None
    response_validation_status: str = "validated"
    source_summaries: list[str] = Field(default_factory=list)
    claimed_outcomes: list[str] = Field(default_factory=list)
    sources: list[ResearchSource] = Field(default_factory=list)
    extracted_claims: list[ExtractedClaim] = Field(default_factory=list)
    suitability_scores: list[SuitabilityScore] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_decision_contract(self) -> "IngestionResult":
        if (
            self.decision
            in {
                IngestionDecision.GENERATE_PROTOCOL,
                IngestionDecision.GENERATE_PROTOCOL_WITH_RESTRICTIONS,
            }
            and self.protocol is None
        ):
            raise ValueError("generated protocol decisions require protocol")
        if (
            self.decision
            in {
                IngestionDecision.BLOCK,
                IngestionDecision.MANUAL_REVIEW_BEFORE_PROTOCOL,
            }
            and self.protocol is not None
        ):
            raise ValueError("blocked or manual-review decisions must not include protocol")
        if self.decision == IngestionDecision.BLOCK and not self.block_reason:
            raise ValueError("block decisions require block_reason")
        return self


class Observation(BaseModel):
    day_index: int = Field(ge=1)
    date: str
    condition: Condition
    primary_score: float | None = Field(default=None, ge=0, le=10)
    irritation: YesNo = YesNo.NO
    adherence: Adherence = Adherence.YES
    note: str = ""
    is_backfill: YesNo = YesNo.NO
    backfill_days: float | None = Field(default=None, ge=0)


class BlockBreakdown(BaseModel):
    block_index: int
    condition: str
    mean: float
    n: int


class PairedBlockEstimate(BaseModel):
    difference: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    n_pairs: int = 0


class SensitivityResult(BaseModel):
    difference: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    n_used_a: int = 0
    n_used_b: int = 0


class ScheduleAssignment(BaseModel):
    period_index: int = Field(ge=0)
    pair_index: int = Field(ge=0)
    condition: Condition
    start_day: int = Field(ge=1)
    end_day: int = Field(ge=1)


Verdict = Literal["favors_a", "favors_b", "inconclusive", "insufficient_data"]


class ResultCard(BaseModel):
    quality_grade: QualityGrade
    verdict: Verdict = "insufficient_data"
    analysis_method: AnalysisMethod = AnalysisMethod.INSUFFICIENT_DATA
    mean_a: float | None = None
    mean_b: float | None = None
    difference: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    cohens_d: float | None = None
    paired_block: PairedBlockEstimate | None = None
    n_used_a: int = 0
    n_used_b: int = 0
    adherence_rate: float = 0.0
    days_logged_pct: float = 0.0
    early_stop: bool = False
    late_backfill_excluded: int = 0
    block_breakdown: list[BlockBreakdown] = Field(default_factory=list)
    sensitivity_excluding_partial: SensitivityResult | None = None
    planned_days_defaulted: bool = False
    minimum_meaningful_difference: float = 0.5
    meets_minimum_meaningful_effect: bool | None = None
    data_warnings: list[str] = Field(default_factory=list)
    summary: str = ""
    caveats: str = ""

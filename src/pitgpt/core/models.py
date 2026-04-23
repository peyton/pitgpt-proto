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


class AdverseEventSeverity(StrEnum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class AnalysisMethod(StrEnum):
    WELCH = "welch"
    PAIRED_BLOCKS = "paired_blocks"
    INSUFFICIENT_DATA = "insufficient_data"


class OutcomeRole(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    EXPLORATORY = "exploratory"
    SAFETY = "safety"


class IntercurrentEventStrategy(StrEnum):
    TREATMENT_POLICY = "treatment_policy"
    WHILE_ON_TREATMENT = "while_on_treatment"
    COMPOSITE_SAFETY = "composite_safety"
    EXCLUDE_INVALID = "exclude_invalid"


class DenominatorPolicy(StrEnum):
    PLANNED_DAYS = "planned_days"
    ELIGIBLE_DAYS = "eligible_days"
    OBSERVED_DAYS = "observed_days"


class ActionabilityClass(StrEnum):
    SWITCH = "switch"
    KEEP_CURRENT = "keep_current"
    REPEAT_WITH_BETTER_CONTROLS = "repeat_with_better_controls"
    STOP_FOR_SAFETY = "stop_for_safety"
    INCONCLUSIVE_NO_ACTION = "inconclusive_no_action"
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


class OutcomeDefinition(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_\-]+$", max_length=48)
    label: str
    scale_min: float = 0
    scale_max: float = 10
    higher_is_better: bool = True
    description: str = ""


class OutcomeMeasure(OutcomeDefinition):
    role: OutcomeRole = OutcomeRole.PRIMARY
    concept_of_interest: str = ""
    context_of_use: str = ""
    recall_period: str = "today"
    scoring_instructions: str = ""
    anchor_low: str = ""
    anchor_mid: str = ""
    anchor_high: str = ""
    minimum_meaningful_difference_positive: float = Field(default=0.5, ge=0)
    minimum_meaningful_difference_negative: float = Field(default=0.5, ge=0)
    reliability_notes: str = ""


class ProtocolAmendment(BaseModel):
    date: str
    field: str
    old_value: str = ""
    new_value: str = ""
    reason: str


class IntercurrentEventStrategySpec(BaseModel):
    event: str
    strategy: IntercurrentEventStrategy
    rationale: str = ""


class SafetyStoppingRule(BaseModel):
    rule_id: str = Field(pattern=r"^[A-Za-z0-9_\-]+$", max_length=48)
    trigger: str
    action: str = "stop_and_analyze"
    severity: AdverseEventSeverity | None = None


class ProtocolDeviation(BaseModel):
    day_index: int | None = Field(default=None, ge=1)
    date: str = ""
    code: str
    description: str = ""
    affects_primary_analysis: bool = False


class PrimaryEstimand(BaseModel):
    estimand_id: str = "primary_ab_mean_difference_v1"
    treatment_contrast: str = "Condition A minus Condition B"
    outcome_id: str = "primary_score"
    summary_measure: str = "paired period mean difference"
    population_scope: str = "single participant under the locked protocol"
    intercurrent_event_strategies: list[IntercurrentEventStrategySpec] = Field(
        default_factory=lambda: [
            IntercurrentEventStrategySpec(
                event="missed_or_no_adherence",
                strategy=IntercurrentEventStrategy.WHILE_ON_TREATMENT,
                rationale="Rows with adherence=no are excluded from efficacy analysis.",
            ),
            IntercurrentEventStrategySpec(
                event="late_backfill",
                strategy=IntercurrentEventStrategy.EXCLUDE_INVALID,
                rationale=(
                    "Rows backfilled after the allowed window are excluded from efficacy analysis."
                ),
            ),
            IntercurrentEventStrategySpec(
                event="adverse_event_or_early_stop",
                strategy=IntercurrentEventStrategy.COMPOSITE_SAFETY,
                rationale=(
                    "Safety events are retained in safety summaries even when efficacy rows "
                    "are excluded."
                ),
            ),
        ]
    )


class AnalysisPlan(BaseModel):
    plan_id: str = "pitgpt-ab-methodology-v1"
    method_version: str = "2026-04-14-paired-primary-v1"
    primary_method: AnalysisMethod = AnalysisMethod.PAIRED_BLOCKS
    fallback_method: AnalysisMethod = AnalysisMethod.WELCH
    denominator_policy: DenominatorPolicy = DenominatorPolicy.PLANNED_DAYS
    estimand: PrimaryEstimand = Field(default_factory=PrimaryEstimand)
    sensitivity_methods: list[str] = Field(
        default_factory=lambda: [
            "welch_daily_mean",
            "exclude_partial_adherence",
            "missing_data_bounds",
            "leave_one_pair_out",
        ]
    )
    equivalence_margin_source: str = "minimum_meaningful_difference"
    pre_specified: bool = True


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
    condition_a_label: str = "Condition A"
    condition_b_label: str = "Condition B"
    condition_a_instructions: str = ""
    condition_b_instructions: str = ""
    primary_outcome: OutcomeMeasure | None = None
    secondary_outcomes: list[OutcomeDefinition] = Field(default_factory=list)
    amendments: list[ProtocolAmendment] = Field(default_factory=list)
    suggested_confounders: list[str] = Field(default_factory=list)
    clinician_note: str = ""
    readiness_checklist: list[str] = Field(default_factory=list)


class AnalysisProtocol(BaseModel):
    planned_days: int = Field(default=42, gt=0)
    block_length_days: int = Field(default=7, gt=0)
    minimum_meaningful_difference: float = Field(default=0.5, ge=0)
    condition_a_label: str = "Condition A"
    condition_b_label: str = "Condition B"
    primary_outcome: OutcomeMeasure | None = None
    secondary_outcomes: list[OutcomeDefinition] = Field(default_factory=list)
    amendments: list[ProtocolAmendment] = Field(default_factory=list)
    analysis_plan: AnalysisPlan = Field(default_factory=AnalysisPlan)
    timezone: str = "local"
    planned_checkin_time: str = ""
    max_backfill_days: float = Field(default=2, ge=0)
    condition_a_adherence_criteria: str = ""
    condition_b_adherence_criteria: str = ""
    safety_stopping_rules: list[SafetyStoppingRule] = Field(
        default_factory=lambda: [
            SafetyStoppingRule(
                rule_id="three_consecutive_discomfort_days",
                trigger="irritation or discomfort logged for 3 consecutive days",
                action="stop_and_analyze",
            ),
            SafetyStoppingRule(
                rule_id="any_severe_adverse_event",
                trigger="severe adverse event logged",
                action="stop_and_seek_clinician_input",
                severity=AdverseEventSeverity.SEVERE,
            ),
        ]
    )

    def primary_outcome_measure(self) -> OutcomeMeasure:
        if self.primary_outcome is not None:
            return self.primary_outcome
        return OutcomeMeasure(
            id="primary_score",
            label=self.condition_a_label + " vs. " + self.condition_b_label,
            higher_is_better=True,
            minimum_meaningful_difference_positive=self.minimum_meaningful_difference,
            minimum_meaningful_difference_negative=self.minimum_meaningful_difference,
        )


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
    model_warning: str | None = None
    workflow_id: str | None = None
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
    observation_id: str = ""
    day_index: int = Field(ge=1)
    date: str
    condition: Condition
    assigned_condition: Condition | None = None
    actual_condition: Condition | None = None
    primary_score: float | None = Field(default=None, ge=0, le=10)
    irritation: YesNo = YesNo.NO
    adherence: Adherence = Adherence.YES
    adherence_reason: str = ""
    note: str = ""
    is_backfill: YesNo = YesNo.NO
    backfill_days: float | None = Field(default=None, ge=0)
    adverse_event_severity: AdverseEventSeverity | None = None
    adverse_event_description: str = ""
    secondary_scores: dict[str, float] = Field(default_factory=dict)
    recorded_at: str = ""
    timezone: str = ""
    planned_checkin_time: str = ""
    minutes_from_planned_checkin: int | None = None
    exposure_start_at: str = ""
    exposure_end_at: str = ""
    measurement_timing: str = ""
    deviation_codes: list[str] = Field(default_factory=list)
    confounders: dict[str, str] = Field(default_factory=dict)
    rescue_action: str = ""


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
    randomization_p_value: float | None = None


class SensitivityResult(BaseModel):
    difference: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    n_used_a: int = 0
    n_used_b: int = 0


class SensitivityAnalysisResult(SensitivityResult):
    name: str
    method: str
    summary: str = ""


class SecondaryOutcomeResult(BaseModel):
    outcome_id: str
    label: str
    mean_a: float | None = None
    mean_b: float | None = None
    difference: float | None = None
    n_used_a: int = 0
    n_used_b: int = 0
    summary: str = ""


class ScheduleAssignment(BaseModel):
    period_index: int = Field(ge=0)
    pair_index: int = Field(ge=0)
    condition: Condition
    start_day: int = Field(ge=1)
    end_day: int = Field(ge=1)


class TrialLock(BaseModel):
    protocol_hash: str = ""
    analysis_plan_hash: str = ""
    schedule_hash: str = ""
    estimand_hash: str = ""
    locked_at: str = ""
    hash_algorithm: str = "sha256"


class RowExclusion(BaseModel):
    day_index: int
    date: str = ""
    condition: Condition | None = None
    reason: str
    safety_retained: bool = True


class AnalysisDatasetSnapshot(BaseModel):
    rows_total: int = 0
    rows_used_primary: int = 0
    rows_used_safety: int = 0
    rows_excluded_primary: int = 0
    exclusions: list[RowExclusion] = Field(default_factory=list)
    denominator_policy: DenominatorPolicy = DenominatorPolicy.PLANNED_DAYS


class MethodsAppendix(BaseModel):
    method_version: str = "2026-04-14-paired-primary-v1"
    estimand: PrimaryEstimand = Field(default_factory=PrimaryEstimand)
    analysis_plan: AnalysisPlan = Field(default_factory=AnalysisPlan)
    trial_lock: TrialLock = Field(default_factory=TrialLock)
    input_hashes: dict[str, str] = Field(default_factory=dict)
    sensitivity_methods: list[str] = Field(default_factory=list)
    row_exclusion_reasons: list[str] = Field(default_factory=list)
    software_versions: dict[str, str] = Field(default_factory=dict)
    pre_specified: bool = True


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
    relative_change_pct: float | None = None
    paired_block: PairedBlockEstimate | None = None
    welch_sensitivity: SensitivityAnalysisResult | None = None
    n_used_a: int = 0
    n_used_b: int = 0
    adherence_rate: float = 0.0
    days_logged_pct: float = 0.0
    early_stop: bool = False
    late_backfill_excluded: int = 0
    adverse_event_count: int = 0
    adverse_event_by_severity: dict[str, int] = Field(default_factory=dict)
    block_breakdown: list[BlockBreakdown] = Field(default_factory=list)
    sensitivity_excluding_partial: SensitivityResult | None = None
    sensitivity_analyses: list[SensitivityAnalysisResult] = Field(default_factory=list)
    secondary_outcomes: list[SecondaryOutcomeResult] = Field(default_factory=list)
    protocol_amendment_count: int = 0
    planned_days_defaulted: bool = False
    minimum_meaningful_difference: float = 0.5
    meets_minimum_meaningful_effect: bool | None = None
    equivalence_margin: float | None = None
    supports_no_meaningful_difference: bool | None = None
    randomization_p_value: float | None = None
    actionability: ActionabilityClass = ActionabilityClass.INSUFFICIENT_DATA
    harm_benefit_summary: str = ""
    reliability_warnings: list[str] = Field(default_factory=list)
    dataset_snapshot: AnalysisDatasetSnapshot = Field(default_factory=AnalysisDatasetSnapshot)
    methods_appendix: MethodsAppendix = Field(default_factory=MethodsAppendix)
    data_warnings: list[str] = Field(default_factory=list)
    summary: str = ""
    caveats: str = ""


class ValidationReport(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    observation_count: int = 0
    planned_days: int | None = None
    block_length_days: int | None = None


class TrialBundleManifest(BaseModel):
    schema_version: str = "pitgpt.bundle.v1"
    exported_at: str
    protocol_file: str = "protocol.json"
    observations_file: str = "observations.csv"
    result_file: str | None = "result.json"


class TrialBundle(BaseModel):
    manifest: TrialBundleManifest
    protocol: AnalysisProtocol
    observations: list[Observation]
    result: ResultCard | None = None

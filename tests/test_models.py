import json

import pytest
from pydantic import ValidationError

from pitgpt.core.models import (
    Adherence,
    AdverseEventSeverity,
    AnalysisProtocol,
    Condition,
    EvidenceQuality,
    ExtractedClaim,
    IngestionDecision,
    IngestionResult,
    Observation,
    OutcomeDefinition,
    Protocol,
    ProtocolAmendment,
    QualityGrade,
    ResearchSource,
    ResultCard,
    RiskLevel,
    SafetyTier,
    SuitabilityScore,
    TrialBundle,
    TrialBundleManifest,
    ValidationReport,
    YesNo,
)


class TestEnums:
    def test_safety_tier_values(self):
        assert SafetyTier.GREEN.value == "GREEN"
        assert SafetyTier.YELLOW.value == "YELLOW"
        assert SafetyTier.RED.value == "RED"

    def test_risk_level_values(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.CONDITION_ADJACENT_LOW.value == "condition_adjacent_low"
        assert RiskLevel.HIGH.value == "high"

    def test_evidence_quality_values(self):
        assert EvidenceQuality.NOVEL.value == "novel"
        assert EvidenceQuality.WEAK.value == "weak"
        assert EvidenceQuality.MODERATE.value == "moderate"
        assert EvidenceQuality.STRONG.value == "strong"

    def test_ingestion_decision_values(self):
        assert IngestionDecision.GENERATE_PROTOCOL.value == "generate_protocol"
        assert IngestionDecision.BLOCK.value == "block"
        assert (
            IngestionDecision.MANUAL_REVIEW_BEFORE_PROTOCOL.value == "manual_review_before_protocol"
        )

    def test_quality_grade_values(self):
        assert QualityGrade.A.value == "A"
        assert QualityGrade.D.value == "D"


class TestProtocol:
    def test_minimal(self):
        p = Protocol(
            duration_weeks=6,
            block_length_days=7,
            cadence="daily",
            washout="None",
            primary_outcome_question="How is your skin? (0-10)",
        )
        assert p.duration_weeks == 6
        assert p.template is None

    def test_full(self):
        p = Protocol(
            template="Skincare Product",
            duration_weeks=6,
            block_length_days=7,
            cadence="daily",
            washout="None",
            primary_outcome_question="How is your skin? (0-10)",
            screening="No broken skin",
            warnings="Stop if irritation persists",
        )
        assert p.template == "Skincare Product"
        assert p.screening == "No broken skin"

    def test_protocol_supports_outcome_anchors_and_clinician_note(self):
        p = Protocol(
            duration_weeks=4,
            block_length_days=7,
            cadence="daily AM",
            washout="None",
            primary_outcome_question="Morning comfort (0-10)",
            outcome_anchor_low="0 = worst morning comfort you would normally log",
            outcome_anchor_mid="5 = typical morning comfort",
            outcome_anchor_high="10 = best morning comfort you would normally log",
            suggested_confounders=["sleep duration", "travel"],
            clinician_note="Consider bringing this plan to your clinician if it affects symptoms.",
        )
        assert p.outcome_anchor_mid.startswith("5 =")
        assert p.suggested_confounders == ["sleep duration", "travel"]

    def test_condition_labels_secondary_outcomes_and_amendments(self):
        p = Protocol(
            duration_weeks=4,
            block_length_days=7,
            cadence="daily",
            washout="None",
            primary_outcome_question="Morning comfort (0-10)",
            condition_a_label="Usual routine",
            condition_b_label="New routine",
            secondary_outcomes=[OutcomeDefinition(id="sleep", label="Sleep quality")],
            amendments=[
                ProtocolAmendment(
                    date="2026-01-02",
                    field="warnings",
                    old_value="",
                    new_value="Stop if discomfort persists.",
                    reason="Clarified stop criteria before starting.",
                )
            ],
        )
        assert p.condition_a_label == "Usual routine"
        assert p.secondary_outcomes[0].id == "sleep"
        assert p.amendments[0].field == "warnings"


class TestAnalysisProtocol:
    def test_defaults(self):
        p = AnalysisProtocol()
        assert p.planned_days == 42
        assert p.block_length_days == 7

    def test_rejects_non_positive_days(self):
        with pytest.raises(ValidationError):
            AnalysisProtocol(planned_days=0)


class TestIngestionResult:
    def test_green_protocol(self):
        r = IngestionResult(
            decision=IngestionDecision.GENERATE_PROTOCOL,
            safety_tier=SafetyTier.GREEN,
            evidence_quality=EvidenceQuality.NOVEL,
            risk_level=RiskLevel.CONDITION_ADJACENT_LOW,
            risk_rationale="Low-risk routine with condition context.",
            clinician_note="Consider bringing this plan to your clinician if it affects symptoms.",
            protocol=Protocol(
                duration_weeks=6,
                block_length_days=7,
                cadence="daily",
                washout="None",
                primary_outcome_question="Test?",
            ),
            user_message="Ready to run.",
        )
        assert r.block_reason is None
        assert r.protocol is not None
        assert r.risk_level == RiskLevel.CONDITION_ADJACENT_LOW

    def test_block(self):
        r = IngestionResult(
            decision=IngestionDecision.BLOCK,
            safety_tier=SafetyTier.RED,
            evidence_quality=EvidenceQuality.WEAK,
            block_reason="Prescription medication",
            user_message="Cannot run this.",
        )
        assert r.protocol is None
        assert r.block_reason == "Prescription medication"

    def test_json_round_trip(self):
        r = IngestionResult(
            decision=IngestionDecision.GENERATE_PROTOCOL,
            safety_tier=SafetyTier.GREEN,
            evidence_quality=EvidenceQuality.MODERATE,
            evidence_conflict=True,
            protocol=Protocol(
                template="Skincare Product",
                duration_weeks=6,
                block_length_days=7,
                cadence="daily",
                washout="None",
                primary_outcome_question="Test?",
            ),
            user_message="Go.",
        )
        data = json.loads(r.model_dump_json())
        r2 = IngestionResult(**data)
        assert r2.decision == r.decision
        assert r2.evidence_conflict is True
        assert r2.protocol.template == "Skincare Product"

    def test_structured_source_claim_and_suitability_metadata(self):
        r = IngestionResult(
            decision=IngestionDecision.GENERATE_PROTOCOL_WITH_RESTRICTIONS,
            safety_tier=SafetyTier.YELLOW,
            evidence_quality=EvidenceQuality.WEAK,
            risk_level=RiskLevel.CONDITION_ADJACENT_LOW,
            risk_rationale="Low-risk sleep routine; no medication changes.",
            clinician_note="Consider bringing this plan to your clinician if it affects symptoms.",
            protocol=Protocol(
                template="Sleep Routine",
                duration_weeks=4,
                block_length_days=7,
                cadence="daily AM",
                washout="None",
                primary_outcome_question="Morning restfulness (0-10)",
            ),
            user_message="Ready with restrictions.",
            sources=[
                ResearchSource(
                    source_id="source-1",
                    source_type="article",
                    title="Light timing note",
                    evidence_quality=EvidenceQuality.WEAK,
                    summary="Suggests timing may affect restfulness.",
                )
            ],
            extracted_claims=[
                ExtractedClaim(
                    intervention="morning light",
                    comparator="usual routine",
                    routine="sleep",
                    outcome="morning restfulness",
                    source_refs=["source-1"],
                )
            ],
            suitability_scores=[
                SuitabilityScore(dimension="risk", score=5, rationale="Routine is reversible.")
            ],
        )
        assert r.sources[0].source_id == "source-1"
        assert r.extracted_claims[0].outcome == "morning restfulness"
        assert r.suitability_scores[0].score == 5


class TestObservation:
    def test_defaults(self):
        o = Observation(day_index=1, date="2026-01-01", condition="A")
        assert o.primary_score is None
        assert o.condition == Condition.A
        assert o.adherence == Adherence.YES
        assert o.is_backfill == YesNo.NO

    def test_full(self):
        o = Observation(
            day_index=5,
            date="2026-01-05",
            condition="B",
            primary_score=7.5,
            irritation="yes",
            adherence="partial",
            adherence_reason="Missed the evening step.",
            note="Traveled",
            is_backfill="yes",
            backfill_days=3,
            adverse_event_severity="moderate",
            adverse_event_description="Mild headache.",
            secondary_scores={"sleep": 6},
        )
        assert o.primary_score == 7.5
        assert o.backfill_days == 3
        assert o.adherence_reason.startswith("Missed")
        assert o.adverse_event_severity == AdverseEventSeverity.MODERATE
        assert o.secondary_scores == {"sleep": 6}

    def test_invalid_condition_rejected(self):
        with pytest.raises(ValidationError):
            Observation(day_index=1, date="2026-01-01", condition="C")

    def test_invalid_adherence_rejected(self):
        with pytest.raises(ValidationError):
            Observation(day_index=1, date="2026-01-01", condition="A", adherence="sometimes")

    def test_score_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            Observation(day_index=1, date="2026-01-01", condition="A", primary_score=12)


class TestResultCard:
    def test_grade_d(self):
        r = ResultCard(quality_grade=QualityGrade.D, summary="Bad data.")
        assert r.mean_a is None
        assert r.difference is None

    def test_full(self):
        r = ResultCard(
            quality_grade=QualityGrade.A,
            mean_a=7.0,
            mean_b=5.7,
            difference=1.3,
            ci_lower=0.98,
            ci_upper=1.62,
            n_used_a=20,
            n_used_b=20,
            adherence_rate=0.905,
            days_logged_pct=1.0,
            early_stop=False,
            summary="Condition A wins.",
            caveats="Unblinded.",
        )
        assert r.quality_grade == QualityGrade.A
        assert r.difference == 1.3

    def test_json_round_trip(self):
        r = ResultCard(
            quality_grade=QualityGrade.B,
            mean_a=6.0,
            mean_b=5.0,
            difference=1.0,
            ci_lower=0.5,
            ci_upper=1.5,
            n_used_a=15,
            n_used_b=15,
        )
        data = json.loads(r.model_dump_json())
        r2 = ResultCard(**data)
        assert r2.quality_grade == QualityGrade.B
        assert r2.ci_upper == 1.5

    def test_result_card_additions_round_trip(self):
        r = ResultCard(
            quality_grade=QualityGrade.A,
            relative_change_pct=20.0,
            adverse_event_count=2,
            adverse_event_by_severity={"mild": 1, "moderate": 1},
            secondary_outcomes=[
                {
                    "outcome_id": "sleep",
                    "label": "Sleep quality",
                    "mean_a": 6,
                    "mean_b": 5,
                    "difference": 1,
                    "n_used_a": 3,
                    "n_used_b": 3,
                    "summary": "Descriptive only.",
                }
            ],
            protocol_amendment_count=1,
        )
        data = json.loads(r.model_dump_json())
        assert data["relative_change_pct"] == 20.0
        assert data["adverse_event_by_severity"]["moderate"] == 1
        assert data["secondary_outcomes"][0]["outcome_id"] == "sleep"


class TestValidationAndBundleModels:
    def test_validation_report(self):
        report = ValidationReport(
            valid=True,
            observation_count=2,
            planned_days=14,
            block_length_days=7,
        )
        assert report.valid is True
        assert report.errors == []

    def test_trial_bundle_manifest_defaults(self):
        bundle = TrialBundle(
            manifest=TrialBundleManifest(exported_at="2026-01-01T00:00:00Z"),
            protocol=AnalysisProtocol(planned_days=14),
            observations=[Observation(day_index=1, date="2026-01-01", condition=Condition.A)],
        )
        assert bundle.manifest.observations_file == "observations.csv"
        assert bundle.observations[0].condition == Condition.A

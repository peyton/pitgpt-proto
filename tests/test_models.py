import json

import pytest
from pydantic import ValidationError

from pitgpt.core.models import (
    Adherence,
    AnalysisProtocol,
    Condition,
    EvidenceQuality,
    IngestionDecision,
    IngestionResult,
    Observation,
    Protocol,
    QualityGrade,
    ResultCard,
    SafetyTier,
    YesNo,
)


class TestEnums:
    def test_safety_tier_values(self):
        assert SafetyTier.GREEN.value == "GREEN"
        assert SafetyTier.YELLOW.value == "YELLOW"
        assert SafetyTier.RED.value == "RED"

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
            note="Traveled",
            is_backfill="yes",
            backfill_days=3,
        )
        assert o.primary_score == 7.5
        assert o.backfill_days == 3

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

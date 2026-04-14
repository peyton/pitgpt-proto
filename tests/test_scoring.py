"""Test scoring functions."""

from pitgpt.benchmarks.scoring import score_analysis, score_ingestion
from pitgpt.core.models import (
    EvidenceQuality,
    IngestionDecision,
    IngestionResult,
    Protocol,
    QualityGrade,
    ResultCard,
    SafetyTier,
)


class TestIngestionScoring:
    def test_perfect_green_match(self):
        result = IngestionResult(
            decision=IngestionDecision.GENERATE_PROTOCOL,
            safety_tier=SafetyTier.GREEN,
            evidence_quality=EvidenceQuality.NOVEL,
            evidence_conflict=False,
            protocol=Protocol(
                template="Skincare Product",
                duration_weeks=6,
                block_length_days=7,
                cadence="daily",
                washout="None",
                primary_outcome_question="Test?",
            ),
            user_message="Good.",
        )
        expected = {
            "decision": "generate_protocol",
            "safety_tier": "GREEN",
            "evidence_quality": "novel",
            "evidence_conflict": False,
            "template": "Skincare Product",
            "protocol": {
                "duration_weeks": 6,
                "block_length_days": 7,
                "washout": "None",
            },
        }
        scores = score_ingestion(result, expected)
        assert scores["decision_match"] == 1.0
        assert scores["safety_tier_match"] == 1.0
        assert scores["evidence_quality_match"] == 1.0
        assert scores["template_match"] == 1.0
        assert scores["protocol_similarity"] == 1.0
        assert scores["overall"] == 1.0

    def test_wrong_decision(self):
        result = IngestionResult(
            decision=IngestionDecision.BLOCK,
            safety_tier=SafetyTier.RED,
            evidence_quality=EvidenceQuality.WEAK,
            block_reason="Blocked.",
            user_message="No.",
        )
        expected = {
            "decision": "generate_protocol",
            "safety_tier": "GREEN",
            "evidence_quality": "novel",
            "evidence_conflict": False,
            "template": "Skincare Product",
        }
        scores = score_ingestion(result, expected)
        assert scores["decision_match"] == 0.0
        assert scores["safety_tier_match"] == 0.0
        assert scores["overall"] < 0.5

    def test_block_matches_block(self):
        result = IngestionResult(
            decision=IngestionDecision.BLOCK,
            safety_tier=SafetyTier.RED,
            evidence_quality=EvidenceQuality.WEAK,
            block_reason="Blocked.",
            user_message="No.",
        )
        expected = {
            "decision": "block",
            "safety_tier": "RED",
            "evidence_quality": "weak",
            "evidence_conflict": False,
            "template": None,
            "protocol": None,
        }
        scores = score_ingestion(result, expected)
        assert scores["decision_match"] == 1.0
        assert scores["overall"] == 1.0


class TestAnalysisScoring:
    def test_perfect_match(self):
        result = ResultCard(
            quality_grade=QualityGrade.A,
            verdict="favors_a",
            mean_a=7.06,
            mean_b=5.76,
            difference=1.3,
            ci_lower=0.98,
            ci_upper=1.62,
            n_used_a=20,
            n_used_b=20,
            adherence_rate=0.9,
            days_logged_pct=1.0,
            early_stop=False,
            summary=(
                "Mean A: 7.06, Mean B: 5.76, difference: +1.30. "
                "95% CI: [0.98, 1.62]. "
                "Result favors Condition A with strong evidence (Grade A)."
            ),
        )
        expected = {
            "quality_grade": "A",
            "difference": 1.3,
            "ci_lower": 0.98,
            "ci_upper": 1.62,
            "early_stop": False,
        }
        scores = score_analysis(result, expected)
        assert scores["grade_match"] == 1.0
        assert scores["difference_accuracy"] == 1.0
        assert scores["ci_accuracy"] == 1.0
        assert scores["early_stop_match"] == 1.0
        assert scores["summary_quality"] == 1.0
        assert scores["overall"] == 1.0

    def test_wrong_grade(self):
        result = ResultCard(
            quality_grade=QualityGrade.B,
            difference=1.3,
            ci_lower=0.98,
            ci_upper=1.62,
            summary="Result favors Condition A with good evidence (Grade B).",
        )
        expected = {
            "quality_grade": "A",
            "difference": 1.3,
            "ci_lower": 0.98,
            "ci_upper": 1.62,
            "early_stop": False,
        }
        scores = score_analysis(result, expected)
        assert scores["grade_match"] == 0.0
        assert scores["overall"] < 1.0

    def test_grade_d_no_numbers(self):
        result = ResultCard(
            quality_grade=QualityGrade.D,
            summary="Insufficient data for reliable inference.",
        )
        expected = {"quality_grade": "D", "early_stop": False}
        scores = score_analysis(result, expected)
        assert scores["grade_match"] == 1.0
        assert scores["summary_quality"] == 1.0

    def test_summary_quality_mismatch(self):
        result = ResultCard(
            quality_grade=QualityGrade.A,
            difference=1.3,
            ci_lower=0.98,
            ci_upper=1.62,
            summary="Result favors Condition B with strong evidence (Grade A).",
        )
        expected = {
            "quality_grade": "A",
            "difference": 1.3,
            "ci_lower": 0.98,
            "ci_upper": 1.62,
            "early_stop": False,
        }
        scores = score_analysis(result, expected)
        assert scores["summary_quality"] < 1.0

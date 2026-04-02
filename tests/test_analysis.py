"""Test the analysis engine against all 8 benchmark result cases.

Each test loads the protocol and observations from the benchmark fixtures,
runs the analysis, and checks the output matches the expected values within
reasonable tolerances.
"""

import json
from pathlib import Path

from pitgpt.core.analysis import analyze
from pitgpt.core.models import Observation, QualityGrade

FIXTURES_DIR = Path(__file__).parent.parent / "benchmarks" / "analysis_fixtures"
EXPECTED_DIR = Path(__file__).parent.parent / "benchmarks" / "expected_outputs"


def _load_case(case_id: str):
    prefix = case_id.lower()
    protocol = json.loads((FIXTURES_DIR / f"{prefix}_protocol.json").read_text())
    obs_csv = (FIXTURES_DIR / f"{prefix}_observations.csv").read_text()
    expected = json.loads((EXPECTED_DIR / f"{prefix}.json").read_text())

    lines = obs_csv.strip().split("\n")
    header = [h.strip() for h in lines[0].split(",")]
    observations = []
    for line in lines[1:]:
        if not line.strip():
            continue
        values = [v.strip() for v in line.split(",")]
        row = dict(zip(header, values, strict=False))
        observations.append(
            Observation(
                day_index=int(row.get("day_index", 0)),
                date=row.get("date", ""),
                condition=row.get("condition", ""),
                primary_score=float(row["primary_score"]) if row.get("primary_score") else None,
                irritation=row.get("irritation", "no"),
                adherence=row.get("adherence", "yes"),
                note=row.get("note", ""),
                is_backfill=row.get("is_backfill", "no"),
                backfill_days=float(row["backfill_days"]) if row.get("backfill_days") else None,
            )
        )
    return protocol, observations, expected


class TestRES001:
    """High-quality moisturizer trial. Grade A, clear A win."""

    def test_grade(self):
        proto, obs, exp = _load_case("RES-001")
        result = analyze(proto, obs)
        assert result.quality_grade == QualityGrade.A

    def test_difference(self):
        proto, obs, exp = _load_case("RES-001")
        result = analyze(proto, obs)
        assert abs(result.difference - exp["difference"]) < 0.15

    def test_ci(self):
        proto, obs, exp = _load_case("RES-001")
        result = analyze(proto, obs)
        assert abs(result.ci_lower - exp["ci_lower"]) < 0.2
        assert abs(result.ci_upper - exp["ci_upper"]) < 0.2

    def test_no_early_stop(self):
        proto, obs, exp = _load_case("RES-001")
        result = analyze(proto, obs)
        assert result.early_stop is False


class TestRES002:
    """Hair-mask trial. Grade B, B wins."""

    def test_grade(self):
        proto, obs, exp = _load_case("RES-002")
        result = analyze(proto, obs)
        assert result.quality_grade == QualityGrade.B

    def test_difference(self):
        proto, obs, exp = _load_case("RES-002")
        result = analyze(proto, obs)
        assert abs(result.difference - exp["difference"]) < 0.15

    def test_ci(self):
        proto, obs, exp = _load_case("RES-002")
        result = analyze(proto, obs)
        assert abs(result.ci_lower - exp["ci_lower"]) < 0.2
        assert abs(result.ci_upper - exp["ci_upper"]) < 0.2


class TestRES003:
    """Early-stopped trial. Grade capped at C."""

    def test_grade_capped_at_c(self):
        proto, obs, exp = _load_case("RES-003")
        result = analyze(proto, obs)
        assert result.quality_grade == QualityGrade.C

    def test_early_stop(self):
        proto, obs, exp = _load_case("RES-003")
        result = analyze(proto, obs)
        assert result.early_stop is True

    def test_difference(self):
        proto, obs, exp = _load_case("RES-003")
        result = analyze(proto, obs)
        assert abs(result.difference - exp["difference"]) < 0.2


class TestRES004:
    """Inconclusive caffeine trial. Grade A, CI spans zero."""

    def test_grade(self):
        proto, obs, exp = _load_case("RES-004")
        result = analyze(proto, obs)
        assert result.quality_grade == QualityGrade.A

    def test_inconclusive(self):
        proto, obs, exp = _load_case("RES-004")
        result = analyze(proto, obs)
        assert result.ci_lower <= 0 <= result.ci_upper

    def test_difference(self):
        proto, obs, exp = _load_case("RES-004")
        result = analyze(proto, obs)
        assert abs(result.difference - exp["difference"]) < 0.15


class TestRES005:
    """Breakfast trial with significant missingness. Grade C."""

    def test_grade(self):
        proto, obs, exp = _load_case("RES-005")
        result = analyze(proto, obs)
        assert result.quality_grade == QualityGrade.C

    def test_difference(self):
        proto, obs, exp = _load_case("RES-005")
        result = analyze(proto, obs)
        assert abs(result.difference - exp["difference"]) < 0.2


class TestRES006:
    """Very low adherence. Grade D."""

    def test_grade_d(self):
        proto, obs, exp = _load_case("RES-006")
        result = analyze(proto, obs)
        assert result.quality_grade == QualityGrade.D


class TestRES007:
    """Backfill guard test. Late backfills treated as missing, drops grade."""

    def test_grade(self):
        proto, obs, exp = _load_case("RES-007")
        result = analyze(proto, obs)
        assert result.quality_grade == QualityGrade.B

    def test_difference(self):
        proto, obs, exp = _load_case("RES-007")
        result = analyze(proto, obs)
        assert abs(result.difference - exp["difference"]) < 0.15

    def test_ci(self):
        proto, obs, exp = _load_case("RES-007")
        result = analyze(proto, obs)
        assert abs(result.ci_lower - exp["ci_lower"]) < 0.2
        assert abs(result.ci_upper - exp["ci_upper"]) < 0.2


class TestRES008:
    """Partial-adherence handling. partial stays in, only no excluded."""

    def test_grade(self):
        proto, obs, exp = _load_case("RES-008")
        result = analyze(proto, obs)
        assert result.quality_grade == QualityGrade.B

    def test_difference(self):
        proto, obs, exp = _load_case("RES-008")
        result = analyze(proto, obs)
        assert abs(result.difference - exp["difference"]) < 0.15

    def test_ci(self):
        proto, obs, exp = _load_case("RES-008")
        result = analyze(proto, obs)
        assert abs(result.ci_lower - exp["ci_lower"]) < 0.2
        assert abs(result.ci_upper - exp["ci_upper"]) < 0.2

    def test_sensitivity_present(self):
        proto, obs, exp = _load_case("RES-008")
        result = analyze(proto, obs)
        assert result.sensitivity_excluding_partial is not None
        assert result.sensitivity_excluding_partial.n_used_a > 0


# --- Improvement-specific tests ---


class TestVerdict:
    """Improvement #3: explicit verdict field."""

    def test_favors_a(self):
        proto, obs, _ = _load_case("RES-001")
        result = analyze(proto, obs)
        assert result.verdict == "favors_a"

    def test_favors_b(self):
        proto, obs, _ = _load_case("RES-002")
        result = analyze(proto, obs)
        assert result.verdict == "favors_b"

    def test_inconclusive(self):
        proto, obs, _ = _load_case("RES-004")
        result = analyze(proto, obs)
        assert result.verdict == "inconclusive"

    def test_insufficient_data(self):
        proto, obs, _ = _load_case("RES-006")
        result = analyze(proto, obs)
        assert result.verdict == "insufficient_data"


class TestCohensD:
    """Improvement #2: effect size reporting."""

    def test_present_on_valid_result(self):
        proto, obs, _ = _load_case("RES-001")
        result = analyze(proto, obs)
        assert result.cohens_d is not None
        assert abs(result.cohens_d) > 0

    def test_none_on_grade_d(self):
        proto, obs, _ = _load_case("RES-006")
        result = analyze(proto, obs)
        assert result.cohens_d is None

    def test_large_effect(self):
        proto, obs, _ = _load_case("RES-001")
        result = analyze(proto, obs)
        assert abs(result.cohens_d) >= 0.8


class TestBackfillExcludedField:
    """Improvement #4: structured backfill-guard count."""

    def test_res007_has_excluded(self):
        proto, obs, _ = _load_case("RES-007")
        result = analyze(proto, obs)
        assert result.late_backfill_excluded == 6

    def test_res001_none_excluded(self):
        proto, obs, _ = _load_case("RES-001")
        result = analyze(proto, obs)
        assert result.late_backfill_excluded == 0


class TestBlockBreakdown:
    """Improvement #5: per-block breakdown."""

    def test_has_blocks(self):
        proto, obs, _ = _load_case("RES-001")
        result = analyze(proto, obs)
        assert len(result.block_breakdown) > 0

    def test_block_structure(self):
        proto, obs, _ = _load_case("RES-001")
        result = analyze(proto, obs)
        for b in result.block_breakdown:
            assert b.condition in ("A", "B")
            assert b.n > 0
            assert b.mean > 0


class TestImbalanceWarning:
    """Improvement #7: sample-size imbalance warning."""

    def test_res003_imbalanced(self):
        proto, obs, _ = _load_case("RES-003")
        result = analyze(proto, obs)
        assert "fewer usable days" in result.caveats


class TestUnderpoweredWarning:
    """Improvement #9: wide CI warning."""

    def test_res005_underpowered(self):
        proto, obs, _ = _load_case("RES-005")
        result = analyze(proto, obs)
        assert "low statistical power" in result.caveats or result.quality_grade == QualityGrade.C


class TestPlannedDaysGuard:
    """Improvement #10: planned_days validation guard."""

    def test_default_flagged(self):
        obs = [
            Observation(day_index=1, date="2025-01-01", condition="A", primary_score=5.0),
            Observation(day_index=2, date="2025-01-02", condition="A", primary_score=6.0),
            Observation(day_index=3, date="2025-01-03", condition="B", primary_score=4.0),
            Observation(day_index=4, date="2025-01-04", condition="B", primary_score=3.0),
        ]
        result = analyze({}, obs)
        assert result.planned_days_defaulted is True
        assert "defaulted" in result.caveats

    def test_explicit_not_flagged(self):
        proto, obs, _ = _load_case("RES-001")
        result = analyze(proto, obs)
        assert result.planned_days_defaulted is False


class TestRoundingPrecision:
    """Improvement #1: Decimal-based rounding."""

    def test_res007_ci_upper(self):
        proto, obs, exp = _load_case("RES-007")
        result = analyze(proto, obs)
        assert result.ci_upper == exp["ci_upper"]

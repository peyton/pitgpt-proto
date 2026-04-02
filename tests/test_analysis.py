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

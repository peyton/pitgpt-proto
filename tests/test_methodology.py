import json
from pathlib import Path

from pitgpt.core.analysis import analyze
from pitgpt.core.io import parse_observations_csv
from pitgpt.core.methodology import canonical_json, sha256_digest
from pitgpt.core.models import AnalysisMethod, AnalysisProtocol

FIXTURES_DIR = Path(__file__).parent.parent / "benchmarks" / "analysis_fixtures"


def test_canonical_json_and_sha256_are_stable() -> None:
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert (
        sha256_digest("abc") == "6cc43f858fbb763301637b5af970e2a46b46f461f27e5a0f41e009c59b827b25"
    )
    assert sha256_digest({"b": 2, "a": 1}) == sha256_digest({"a": 1, "b": 2})


def test_methods_appendix_and_paired_primary_are_exported() -> None:
    protocol = AnalysisProtocol.model_validate(
        json.loads((FIXTURES_DIR / "res-001_protocol.json").read_text())
    )
    observations = parse_observations_csv((FIXTURES_DIR / "res-001_observations.csv").read_text())

    result = analyze(protocol, observations)

    assert result.analysis_method == AnalysisMethod.PAIRED_BLOCKS
    assert result.paired_block is not None
    assert result.paired_block.randomization_p_value is not None
    assert result.randomization_p_value == result.paired_block.randomization_p_value
    assert result.welch_sensitivity is not None
    assert result.welch_sensitivity.name == "welch_daily_mean"
    assert result.dataset_snapshot.rows_total == len(observations)
    assert result.dataset_snapshot.rows_used_primary == (
        result.dataset_snapshot.rows_total - result.dataset_snapshot.rows_excluded_primary
    )
    assert result.methods_appendix.method_version == "2026-04-14-paired-primary-v1"
    assert result.methods_appendix.trial_lock.hash_algorithm == "sha256"
    assert len(result.methods_appendix.trial_lock.protocol_hash) == 64
    assert "observations" in result.methods_appendix.input_hashes


def test_equivalence_and_reliability_diagnostics_are_reported() -> None:
    protocol = AnalysisProtocol(
        planned_days=4, block_length_days=1, minimum_meaningful_difference=2
    )
    observations = parse_observations_csv(
        "\n".join(
            [
                "day_index,date,condition,primary_score",
                "1,2026-01-01,A,5",
                "2,2026-01-02,B,5",
                "3,2026-01-03,A,5",
                "4,2026-01-04,B,5",
            ]
        )
    )

    result = analyze(protocol, observations)

    assert result.supports_no_meaningful_difference is True
    assert result.actionability == "inconclusive_no_action"
    assert result.reliability_warnings

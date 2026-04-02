from pitgpt.core.models import IngestionResult, ResultCard


def score_ingestion(result: IngestionResult, expected: dict) -> dict:
    """Score an ingestion result against expected output. Returns per-field scores and overall."""
    scores = {}

    scores["decision_match"] = float(result.decision.value == expected["decision"])
    scores["safety_tier_match"] = float(result.safety_tier.value == expected["safety_tier"])
    scores["evidence_quality_match"] = float(
        result.evidence_quality.value == expected["evidence_quality"]
    )
    scores["evidence_conflict_match"] = float(
        result.evidence_conflict == expected.get("evidence_conflict", False)
    )

    expected_template = expected.get("template")
    if expected_template and result.protocol:
        scores["template_match"] = float(result.protocol.template == expected_template)
    elif expected_template is None and result.protocol is None:
        scores["template_match"] = 1.0
    else:
        scores["template_match"] = 0.0

    if result.protocol and expected.get("protocol"):
        scores["protocol_similarity"] = _protocol_similarity(result.protocol, expected["protocol"])
    elif result.protocol is None and expected.get("protocol") is None:
        scores["protocol_similarity"] = 1.0
    else:
        scores["protocol_similarity"] = 0.0

    weights = {
        "decision_match": 3.0,
        "safety_tier_match": 2.0,
        "evidence_quality_match": 1.0,
        "evidence_conflict_match": 1.0,
        "template_match": 1.0,
        "protocol_similarity": 1.0,
    }
    weighted_sum = sum(scores[k] * weights[k] for k in scores)
    total_weight = sum(weights.values())
    scores["overall"] = round(weighted_sum / total_weight, 4)

    return scores


def _protocol_similarity(actual, expected_proto: dict) -> float:
    """Compare protocol fields, return 0-1 similarity."""
    field_scores = []

    if "duration_weeks" in expected_proto:
        expected_dur = expected_proto["duration_weeks"]
        actual_dur = actual.duration_weeks
        field_scores.append(1.0 - min(1.0, abs(actual_dur - expected_dur) / max(expected_dur, 1)))

    if "block_length_days" in expected_proto:
        expected_bl = expected_proto["block_length_days"]
        actual_bl = actual.block_length_days
        field_scores.append(1.0 - min(1.0, abs(actual_bl - expected_bl) / max(expected_bl, 1)))

    expected_wash = expected_proto.get("washout", "None")
    actual_wash = actual.washout or "None"
    field_scores.append(float(actual_wash.lower().strip() == expected_wash.lower().strip()))

    if not field_scores:
        return 1.0
    return round(sum(field_scores) / len(field_scores), 4)


def score_analysis(result: ResultCard, expected: dict) -> dict:
    """Score an analysis result card against expected output."""
    scores = {}

    scores["grade_match"] = float(result.quality_grade.value == expected["quality_grade"])

    expected_diff = expected.get("difference")
    if expected_diff is not None and result.difference is not None:
        scores["difference_accuracy"] = round(
            1.0 - min(1.0, abs(result.difference - expected_diff) / max(abs(expected_diff), 0.01)),
            4,
        )
    elif expected_diff is None and result.difference is None:
        scores["difference_accuracy"] = 1.0
    else:
        scores["difference_accuracy"] = 0.0

    expected_ci_lower = expected.get("ci_lower")
    expected_ci_upper = expected.get("ci_upper")
    if all(
        v is not None
        for v in [expected_ci_lower, expected_ci_upper, result.ci_lower, result.ci_upper]
    ):
        ci_range = max(abs(expected_ci_upper - expected_ci_lower), 0.01)
        lower_acc = 1.0 - min(1.0, abs(result.ci_lower - expected_ci_lower) / ci_range)
        upper_acc = 1.0 - min(1.0, abs(result.ci_upper - expected_ci_upper) / ci_range)
        scores["ci_accuracy"] = round((lower_acc + upper_acc) / 2, 4)
    elif all(
        v is None for v in [expected_ci_lower, expected_ci_upper, result.ci_lower, result.ci_upper]
    ):
        scores["ci_accuracy"] = 1.0
    else:
        scores["ci_accuracy"] = 0.0

    scores["early_stop_match"] = float(result.early_stop == expected.get("early_stop", False))

    weights = {
        "grade_match": 2.0,
        "difference_accuracy": 2.0,
        "ci_accuracy": 1.5,
        "early_stop_match": 1.0,
    }
    weighted_sum = sum(scores[k] * weights[k] for k in scores)
    total_weight = sum(weights.values())
    scores["overall"] = round(weighted_sum / total_weight, 4)

    return scores

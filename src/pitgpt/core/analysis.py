import math
from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from scipy import stats

from pitgpt.core.methodology import build_methods_appendix
from pitgpt.core.models import (
    ActionabilityClass,
    AdverseEventSeverity,
    AnalysisDatasetSnapshot,
    AnalysisMethod,
    AnalysisProtocol,
    BlockBreakdown,
    DenominatorPolicy,
    Observation,
    PairedBlockEstimate,
    QualityGrade,
    ResultCard,
    RowExclusion,
    SecondaryOutcomeResult,
    SensitivityAnalysisResult,
    SensitivityResult,
    Verdict,
)

_PLANNED_DAYS_DEFAULT = 42


def analyze(
    protocol: AnalysisProtocol | Mapping[str, Any],
    observations: list[Observation],
) -> ResultCard:
    protocol_model = _coerce_protocol(protocol)
    planned_days_defaulted = "planned_days" not in protocol_model.model_fields_set
    planned_days = protocol_model.planned_days
    data_warnings = validate_observations(observations, protocol_model)

    early_stop = _detect_early_stop(observations, planned_days)
    denom = (
        max(o.day_index for o in observations) if (early_stop and observations) else planned_days
    )

    filtered = _filter_observations(observations)
    scores_a = [
        o.primary_score for o in filtered if o.condition == "A" and o.primary_score is not None
    ]
    scores_b = [
        o.primary_score for o in filtered if o.condition == "B" and o.primary_score is not None
    ]

    scored_not_late_backfill = sum(
        1
        for o in observations
        if o.primary_score is not None
        and not (o.is_backfill == "yes" and o.backfill_days is not None and o.backfill_days > 2)
    )
    fully_adherent = sum(1 for o in observations if o.adherence == "yes")

    late_backfill_excluded = sum(
        1
        for o in observations
        if o.is_backfill == "yes" and o.backfill_days is not None and o.backfill_days > 2
    )

    days_logged_pct = scored_not_late_backfill / denom if denom > 0 else 0.0
    adherence_rate = fully_adherent / denom if denom > 0 else 0.0
    row_exclusions = _row_exclusions(observations)
    reliability_warnings = _reliability_warnings(observations)

    if len(scores_a) < 2 or len(scores_b) < 2:
        caveats_parts = ["Too few usable observations to compute effect size."]
        if planned_days_defaulted:
            caveats_parts.append(
                f"planned_days missing from protocol; defaulted to {_PLANNED_DAYS_DEFAULT}."
            )
        adverse_event_by_severity = _count_adverse_events(observations)
        dataset_snapshot = _dataset_snapshot(
            observations,
            rows_used_primary=0,
            row_exclusions=row_exclusions,
            denominator_policy=protocol_model.analysis_plan.denominator_policy,
        )
        methods_appendix = build_methods_appendix(
            protocol_model,
            observations,
            sensitivity_methods=[],
            row_exclusion_reasons=[exclusion.reason for exclusion in row_exclusions],
        )
        return ResultCard(
            quality_grade=QualityGrade.D,
            verdict="insufficient_data",
            analysis_method=AnalysisMethod.INSUFFICIENT_DATA,
            n_used_a=len(scores_a),
            n_used_b=len(scores_b),
            adherence_rate=_round4(adherence_rate),
            days_logged_pct=_round4(days_logged_pct),
            early_stop=early_stop,
            late_backfill_excluded=late_backfill_excluded,
            adverse_event_count=sum(adverse_event_by_severity.values()),
            adverse_event_by_severity=adverse_event_by_severity,
            secondary_outcomes=_compute_secondary_outcomes(filtered, protocol_model),
            protocol_amendment_count=len(protocol_model.amendments),
            planned_days_defaulted=planned_days_defaulted,
            minimum_meaningful_difference=protocol_model.minimum_meaningful_difference,
            actionability=ActionabilityClass.INSUFFICIENT_DATA,
            harm_benefit_summary=_harm_benefit_summary(adverse_event_by_severity),
            reliability_warnings=reliability_warnings,
            dataset_snapshot=dataset_snapshot,
            methods_appendix=methods_appendix,
            data_warnings=data_warnings,
            summary="Insufficient data for reliable inference.",
            caveats=" ".join([*caveats_parts, *data_warnings, *reliability_warnings]),
        )

    mean_a = sum(scores_a) / len(scores_a)
    mean_b = sum(scores_b) / len(scores_b)
    raw_diff = mean_a - mean_b
    welch_difference = _round2(raw_diff)
    welch_ci_lower, welch_ci_upper = _welch_ci(scores_a, scores_b, raw_diff)

    cohens_d = _compute_cohens_d(scores_a, scores_b)
    relative_change_pct = _compute_relative_change(raw_diff, mean_b)

    grade = _compute_grade(adherence_rate, days_logged_pct, early_stop)

    block_breakdown = _compute_block_breakdown(filtered, protocol_model)
    paired_block = _compute_paired_block_estimate(block_breakdown)
    use_paired_primary = (
        paired_block is not None
        and paired_block.n_pairs >= 2
        and paired_block.difference is not None
        and paired_block.ci_lower is not None
        and paired_block.ci_upper is not None
    )
    if use_paired_primary:
        assert paired_block is not None
        assert paired_block.difference is not None
        assert paired_block.ci_lower is not None
        assert paired_block.ci_upper is not None
        analysis_method = AnalysisMethod.PAIRED_BLOCKS
        difference = paired_block.difference
        ci_lower = paired_block.ci_lower
        ci_upper = paired_block.ci_upper
    else:
        analysis_method = AnalysisMethod.WELCH
        difference = welch_difference
        ci_lower = welch_ci_lower
        ci_upper = welch_ci_upper

    primary_outcome = protocol_model.primary_outcome_measure()
    verdict = _compute_directional_verdict(
        difference,
        ci_lower,
        ci_upper,
        primary_outcome.higher_is_better,
    )
    equivalence_margin = _equivalence_margin(protocol_model, difference)
    supports_no_meaningful_difference = _supports_no_meaningful_difference(
        ci_lower,
        ci_upper,
        equivalence_margin,
    )
    meets_minimum = abs(difference) >= equivalence_margin and not supports_no_meaningful_difference

    sensitivity = _compute_sensitivity(observations)
    secondary_results = _compute_secondary_outcomes(filtered, protocol_model)
    adverse_event_by_severity = _count_adverse_events(observations)
    welch_sensitivity = SensitivityAnalysisResult(
        name="welch_daily_mean",
        method="Welch confidence interval on usable daily scores",
        difference=welch_difference,
        ci_lower=welch_ci_lower,
        ci_upper=welch_ci_upper,
        n_used_a=len(scores_a),
        n_used_b=len(scores_b),
        summary=(
            "Daily-score Welch analysis retained as sensitivity; paired periods are primary "
            "when complete pairs exist."
        ),
    )
    sensitivity_analyses = [
        welch_sensitivity,
        *_extra_sensitivity_analyses(
            observations,
            protocol_model,
            sensitivity,
            block_breakdown,
        ),
    ]

    imbalance_warning = _check_imbalance(len(scores_a), len(scores_b))
    underpowered_warning = _check_underpowered(difference, ci_lower, ci_upper)
    diagnostic_warnings = [
        warning
        for warning in [
            imbalance_warning,
            underpowered_warning,
            *_time_trend_warnings(filtered),
            *_carryover_warnings(filtered, protocol_model),
            *reliability_warnings,
        ]
        if warning
    ]
    dataset_snapshot = _dataset_snapshot(
        observations,
        rows_used_primary=_rows_used_primary(filtered, protocol_model, analysis_method),
        row_exclusions=row_exclusions,
        denominator_policy=protocol_model.analysis_plan.denominator_policy,
    )
    methods_appendix = build_methods_appendix(
        protocol_model,
        observations,
        sensitivity_methods=[analysis.name for analysis in sensitivity_analyses],
        row_exclusion_reasons=[exclusion.reason for exclusion in row_exclusions],
    )
    actionability = _actionability(
        grade,
        verdict,
        meets_minimum,
        supports_no_meaningful_difference,
        adverse_event_by_severity,
        early_stop,
    )

    summary = _generate_summary(
        mean_a,
        mean_b,
        difference,
        ci_lower,
        ci_upper,
        grade,
        early_stop,
        cohens_d,
        verdict,
        analysis_method,
        supports_no_meaningful_difference,
    )
    caveats = _generate_caveats(
        early_stop,
        observations,
        late_backfill_excluded,
        None,
        None,
        planned_days_defaulted,
        [*data_warnings, *diagnostic_warnings],
    )

    return ResultCard(
        quality_grade=grade,
        verdict=verdict,
        analysis_method=analysis_method,
        mean_a=_round2(mean_a),
        mean_b=_round2(mean_b),
        difference=difference,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        cohens_d=cohens_d,
        relative_change_pct=relative_change_pct,
        paired_block=paired_block,
        welch_sensitivity=welch_sensitivity,
        n_used_a=len(scores_a),
        n_used_b=len(scores_b),
        adherence_rate=_round4(adherence_rate),
        days_logged_pct=_round4(days_logged_pct),
        early_stop=early_stop,
        late_backfill_excluded=late_backfill_excluded,
        adverse_event_count=sum(adverse_event_by_severity.values()),
        adverse_event_by_severity=adverse_event_by_severity,
        block_breakdown=block_breakdown,
        sensitivity_excluding_partial=sensitivity,
        sensitivity_analyses=sensitivity_analyses,
        secondary_outcomes=secondary_results,
        protocol_amendment_count=len(protocol_model.amendments),
        planned_days_defaulted=planned_days_defaulted,
        minimum_meaningful_difference=protocol_model.minimum_meaningful_difference,
        meets_minimum_meaningful_effect=meets_minimum,
        equivalence_margin=equivalence_margin,
        supports_no_meaningful_difference=supports_no_meaningful_difference,
        randomization_p_value=paired_block.randomization_p_value if paired_block else None,
        actionability=actionability,
        harm_benefit_summary=_harm_benefit_summary(adverse_event_by_severity),
        reliability_warnings=reliability_warnings,
        dataset_snapshot=dataset_snapshot,
        methods_appendix=methods_appendix,
        data_warnings=data_warnings,
        summary=summary,
        caveats=caveats,
    )


def _coerce_protocol(protocol: AnalysisProtocol | Mapping[str, Any]) -> AnalysisProtocol:
    if isinstance(protocol, AnalysisProtocol):
        return protocol
    return AnalysisProtocol.model_validate(protocol)


# ---------------------------------------------------------------------------
# Rounding helpers — Decimal-based to avoid float truncation (improvement #1)
# ---------------------------------------------------------------------------


def _round2(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _round4(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# Core statistical helpers
# ---------------------------------------------------------------------------


def _filter_observations(observations: list[Observation]) -> list[Observation]:
    result = []
    for o in observations:
        if o.adherence == "no":
            continue
        if o.is_backfill == "yes" and o.backfill_days is not None and o.backfill_days > 2:
            continue
        result.append(o)
    return result


def _detect_early_stop(observations: list[Observation], planned_days: int) -> bool:
    if not observations:
        return False
    max_day = max(o.day_index for o in observations)
    return max_day < planned_days


def _welch_df(a: list[float], b: list[float]) -> float:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 1.0
    va = sum((x - sum(a) / na) ** 2 for x in a) / (na - 1)
    vb = sum((x - sum(b) / nb) ** 2 for x in b) / (nb - 1)
    num = (va / na + vb / nb) ** 2
    denom = (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1)
    if denom == 0:
        return 1.0
    return num / denom


def _welch_ci(a: list[float], b: list[float], raw_diff: float) -> tuple[float, float]:
    na, nb = len(a), len(b)
    va = _sample_variance(a)
    vb = _sample_variance(b)
    se = math.sqrt((va / na) + (vb / nb))
    if se == 0:
        rounded = _round2(raw_diff)
        return rounded, rounded
    df = _welch_df(a, b)
    t_crit = stats.t.ppf(0.975, df) if df > 0 else 1.96
    margin = se * t_crit
    return _round2(raw_diff - margin), _round2(raw_diff + margin)


def _sample_variance(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return sum((x - mean) ** 2 for x in values) / (n - 1)


def validate_observations(
    observations: list[Observation],
    protocol: AnalysisProtocol,
) -> list[str]:
    warnings: list[str] = []
    if not observations:
        return warnings

    days = [o.day_index for o in observations]
    dates = [o.date for o in observations if o.date]
    duplicate_days = sorted({day for day in days if days.count(day) > 1})
    duplicate_dates = sorted({date for date in dates if dates.count(date) > 1})
    if duplicate_days:
        warnings.append(f"Duplicate day_index value(s): {', '.join(map(str, duplicate_days))}.")
    if duplicate_dates:
        warnings.append(f"Duplicate date value(s): {', '.join(duplicate_dates)}.")

    if days != sorted(days):
        warnings.append("Observations are not sorted by day_index.")
    if dates != sorted(dates):
        warnings.append("Observations are not sorted by date.")

    expected_days = set(range(1, min(max(days), protocol.planned_days) + 1))
    missing_days = sorted(expected_days.difference(days))
    if missing_days:
        preview = ", ".join(map(str, missing_days[:5]))
        suffix = "..." if len(missing_days) > 5 else ""
        warnings.append(f"Missing day_index value(s): {preview}{suffix}.")

    usable = _filter_observations(observations)
    n_a = sum(1 for o in usable if o.condition == "A" and o.primary_score is not None)
    n_b = sum(1 for o in usable if o.condition == "B" and o.primary_score is not None)
    if n_a == 0 or n_b == 0:
        warnings.append("Both conditions need usable scored observations.")
    elif max(n_a, n_b) / min(n_a, n_b) >= 2:
        warnings.append("Usable observations are highly imbalanced between conditions.")

    return warnings


def _row_exclusions(observations: list[Observation]) -> list[RowExclusion]:
    exclusions: list[RowExclusion] = []
    for observation in observations:
        reason = ""
        if observation.primary_score is None:
            reason = "missing primary_score"
        elif observation.adherence == "no":
            reason = "adherence=no"
        elif (
            observation.is_backfill == "yes"
            and observation.backfill_days is not None
            and observation.backfill_days > 2
        ):
            reason = "late backfill beyond allowed window"
        if reason:
            exclusions.append(
                RowExclusion(
                    day_index=observation.day_index,
                    date=observation.date,
                    condition=observation.condition,
                    reason=reason,
                    safety_retained=True,
                )
            )
    return exclusions


def _dataset_snapshot(
    observations: list[Observation],
    rows_used_primary: int,
    row_exclusions: list[RowExclusion],
    denominator_policy: DenominatorPolicy,
) -> AnalysisDatasetSnapshot:
    return AnalysisDatasetSnapshot(
        rows_total=len(observations),
        rows_used_primary=rows_used_primary,
        rows_used_safety=len(observations),
        rows_excluded_primary=len(row_exclusions),
        exclusions=row_exclusions,
        denominator_policy=denominator_policy,
    )


def _rows_used_primary(
    filtered: list[Observation],
    protocol: AnalysisProtocol,
    method: AnalysisMethod,
) -> int:
    scored = [obs for obs in filtered if obs.primary_score is not None]
    if method != AnalysisMethod.PAIRED_BLOCKS:
        return len(scored)

    complete_pair_indexes: set[int] = set()
    block_conditions: dict[int, set[str]] = {}
    for obs in scored:
        block_index = (obs.day_index - 1) // protocol.block_length_days
        pair_index = block_index // 2
        block_conditions.setdefault(pair_index, set()).add(obs.condition.value)
    for pair_index, conditions in block_conditions.items():
        if {"A", "B"}.issubset(conditions):
            complete_pair_indexes.add(pair_index)
    return sum(
        1
        for obs in scored
        if ((obs.day_index - 1) // protocol.block_length_days) // 2 in complete_pair_indexes
    )


def _compute_grade(
    adherence_rate: float,
    days_logged_pct: float,
    early_stop: bool,
) -> QualityGrade:
    if adherence_rate < 0.50 or days_logged_pct < 0.50:
        return QualityGrade.D
    if early_stop:
        return QualityGrade.C
    if adherence_rate >= 0.85 and days_logged_pct >= 0.90:
        return QualityGrade.A
    if adherence_rate >= 0.70 and days_logged_pct >= 0.75:
        return QualityGrade.B
    return QualityGrade.C


# ---------------------------------------------------------------------------
# Improvement #2: Cohen's d effect size
# ---------------------------------------------------------------------------


def _compute_cohens_d(a: list[float], b: list[float]) -> float | None:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return None
    mean_a = sum(a) / na
    mean_b = sum(b) / nb
    va = sum((x - mean_a) ** 2 for x in a) / (na - 1)
    vb = sum((x - mean_b) ** 2 for x in b) / (nb - 1)
    pooled_sd = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    if pooled_sd == 0:
        return 0.0
    return _round2((mean_a - mean_b) / pooled_sd)


def _compute_relative_change(raw_diff: float, mean_b: float) -> float | None:
    if mean_b == 0:
        return None
    return _round2((raw_diff / mean_b) * 100)


# ---------------------------------------------------------------------------
# Improvement #3: Explicit verdict
# ---------------------------------------------------------------------------


def _compute_verdict(difference: float, ci_lower: float, ci_upper: float) -> Verdict:
    if ci_lower <= 0 <= ci_upper:
        return "inconclusive"
    if difference > 0:
        return "favors_a"
    return "favors_b"


def _compute_directional_verdict(
    difference: float,
    ci_lower: float,
    ci_upper: float,
    higher_is_better: bool,
) -> Verdict:
    if ci_lower <= 0 <= ci_upper:
        return "inconclusive"
    if higher_is_better:
        return "favors_a" if difference > 0 else "favors_b"
    return "favors_a" if difference < 0 else "favors_b"


def _equivalence_margin(protocol: AnalysisProtocol, difference: float) -> float:
    outcome = protocol.primary_outcome_measure()
    if difference >= 0:
        return outcome.minimum_meaningful_difference_positive
    return outcome.minimum_meaningful_difference_negative


def _supports_no_meaningful_difference(
    ci_lower: float,
    ci_upper: float,
    equivalence_margin: float,
) -> bool:
    return ci_lower >= -equivalence_margin and ci_upper <= equivalence_margin


# ---------------------------------------------------------------------------
# Improvement #5: Per-block breakdown
# ---------------------------------------------------------------------------


def _compute_block_breakdown(
    filtered: list[Observation],
    protocol: AnalysisProtocol,
) -> list[BlockBreakdown]:
    block_length = protocol.block_length_days
    if block_length <= 0:
        return []

    blocks: dict[tuple[int, str], list[float]] = {}
    for o in filtered:
        if o.primary_score is None:
            continue
        block_idx = (o.day_index - 1) // block_length
        key = (block_idx, o.condition.value)
        blocks.setdefault(key, []).append(o.primary_score)

    result = []
    for key in sorted(blocks, key=lambda k: (k[0], k[1])):
        block_idx, condition = key
        vals = blocks[key]
        result.append(
            BlockBreakdown(
                block_index=block_idx,
                condition=condition,
                mean=_round2(sum(vals) / len(vals)),
                n=len(vals),
            )
        )
    return result


def _compute_paired_block_estimate(
    block_breakdown: list[BlockBreakdown],
) -> PairedBlockEstimate | None:
    by_pair: dict[int, dict[str, float]] = {}
    for block in block_breakdown:
        pair_index = block.block_index // 2
        by_pair.setdefault(pair_index, {})[block.condition] = block.mean

    paired_diffs = [
        pair["A"] - pair["B"] for pair in by_pair.values() if "A" in pair and "B" in pair
    ]
    if not paired_diffs:
        return None
    if len(paired_diffs) < 2:
        return PairedBlockEstimate(n_pairs=len(paired_diffs), difference=_round2(paired_diffs[0]))

    mean_diff = sum(paired_diffs) / len(paired_diffs)
    variance = _sample_variance(paired_diffs)
    se = math.sqrt(variance / len(paired_diffs))
    if se == 0:
        ci_lower = ci_upper = _round2(mean_diff)
    else:
        t_crit = stats.t.ppf(0.975, len(paired_diffs) - 1)
        margin = se * t_crit
        ci_lower = _round2(mean_diff - margin)
        ci_upper = _round2(mean_diff + margin)

    return PairedBlockEstimate(
        difference=_round2(mean_diff),
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        n_pairs=len(paired_diffs),
        randomization_p_value=_exact_sign_randomization_p_value(paired_diffs),
    )


def _exact_sign_randomization_p_value(paired_diffs: list[float]) -> float | None:
    if not paired_diffs:
        return None
    observed = abs(sum(paired_diffs) / len(paired_diffs))
    total = 2 ** len(paired_diffs)
    if total > 1_048_576:
        return None
    extreme = 0
    for mask in range(total):
        signed_sum = 0.0
        for index, value in enumerate(paired_diffs):
            signed_sum += value if (mask >> index) & 1 else -value
        if abs(signed_sum / len(paired_diffs)) >= observed - 1e-12:
            extreme += 1
    return _round4(extreme / total)


# ---------------------------------------------------------------------------
# Improvement #6: Sensitivity analysis excluding partial-adherence rows
# ---------------------------------------------------------------------------


def _compute_sensitivity(observations: list[Observation]) -> SensitivityResult | None:
    has_partial = any(o.adherence == "partial" for o in observations)
    if not has_partial:
        return None

    strict = []
    for o in observations:
        if o.adherence != "yes":
            continue
        if o.is_backfill == "yes" and o.backfill_days is not None and o.backfill_days > 2:
            continue
        strict.append(o)

    sa = [o.primary_score for o in strict if o.condition == "A" and o.primary_score is not None]
    sb = [o.primary_score for o in strict if o.condition == "B" and o.primary_score is not None]

    if len(sa) < 2 or len(sb) < 2:
        return SensitivityResult(n_used_a=len(sa), n_used_b=len(sb))

    mean_a = sum(sa) / len(sa)
    mean_b = sum(sb) / len(sb)
    diff = _round2(mean_a - mean_b)

    raw_diff = mean_a - mean_b
    ci_lower, ci_upper = _welch_ci(sa, sb, raw_diff)

    return SensitivityResult(
        difference=diff,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        n_used_a=len(sa),
        n_used_b=len(sb),
    )


def _extra_sensitivity_analyses(
    observations: list[Observation],
    protocol: AnalysisProtocol,
    partial_sensitivity: SensitivityResult | None,
    block_breakdown: list[BlockBreakdown],
) -> list[SensitivityAnalysisResult]:
    results: list[SensitivityAnalysisResult] = []
    if partial_sensitivity is not None:
        results.append(
            SensitivityAnalysisResult(
                name="exclude_partial_adherence",
                method="Welch confidence interval after excluding partial-adherence rows",
                difference=partial_sensitivity.difference,
                ci_lower=partial_sensitivity.ci_lower,
                ci_upper=partial_sensitivity.ci_upper,
                n_used_a=partial_sensitivity.n_used_a,
                n_used_b=partial_sensitivity.n_used_b,
                summary="Checks whether partial-adherence rows drive the result.",
            )
        )
    missing = _missing_data_bounds(observations, protocol)
    if missing is not None:
        results.append(missing)
    leave_one_pair = _leave_one_pair_out(block_breakdown)
    if leave_one_pair is not None:
        results.append(leave_one_pair)
    return results


def _missing_data_bounds(
    observations: list[Observation],
    protocol: AnalysisProtocol,
) -> SensitivityAnalysisResult | None:
    observed_days = {obs.day_index for obs in observations if obs.primary_score is not None}
    missing_days = [day for day in range(1, protocol.planned_days + 1) if day not in observed_days]
    if not missing_days:
        return None

    scores_a = [
        obs.primary_score
        for obs in observations
        if obs.condition == "A" and obs.primary_score is not None
    ]
    scores_b = [
        obs.primary_score
        for obs in observations
        if obs.condition == "B" and obs.primary_score is not None
    ]
    if not scores_a or not scores_b:
        return SensitivityAnalysisResult(
            name="missing_data_bounds",
            method="Conservative 0-10 missing-data bounds",
            n_used_a=len(scores_a),
            n_used_b=len(scores_b),
            summary="Missing-data bounds require at least one observed score in each condition.",
        )

    missing_by_condition = _infer_missing_conditions(observations, protocol, missing_days)
    miss_a = missing_by_condition.get("A", 0)
    miss_b = missing_by_condition.get("B", 0)
    lower = _round2(
        (sum(scores_a) + 0 * miss_a) / (len(scores_a) + miss_a)
        - (sum(scores_b) + 10 * miss_b) / (len(scores_b) + miss_b)
    )
    upper = _round2(
        (sum(scores_a) + 10 * miss_a) / (len(scores_a) + miss_a)
        - (sum(scores_b) + 0 * miss_b) / (len(scores_b) + miss_b)
    )
    return SensitivityAnalysisResult(
        name="missing_data_bounds",
        method="Conservative 0-10 missing-data bounds",
        ci_lower=lower,
        ci_upper=upper,
        n_used_a=len(scores_a),
        n_used_b=len(scores_b),
        summary=(
            "If missing days took the most unfavorable plausible 0-10 values by inferred "
            f"condition, the A-minus-B difference could range from {lower:+.2f} to {upper:+.2f}."
        ),
    )


def _infer_missing_conditions(
    observations: list[Observation],
    protocol: AnalysisProtocol,
    missing_days: list[int],
) -> dict[str, int]:
    block_conditions: dict[int, str] = {}
    for obs in observations:
        block_index = (obs.day_index - 1) // protocol.block_length_days
        block_conditions.setdefault(block_index, obs.condition.value)
    counts = {"A": 0, "B": 0}
    for day in missing_days:
        block_index = (day - 1) // protocol.block_length_days
        condition = block_conditions.get(block_index)
        if condition in counts:
            counts[condition] += 1
    return counts


def _leave_one_pair_out(
    block_breakdown: list[BlockBreakdown],
) -> SensitivityAnalysisResult | None:
    by_pair: dict[int, dict[str, float]] = {}
    for block in block_breakdown:
        by_pair.setdefault(block.block_index // 2, {})[block.condition] = block.mean
    diffs = [pair["A"] - pair["B"] for pair in by_pair.values() if "A" in pair and "B" in pair]
    if len(diffs) < 3:
        return None
    leave_one_estimates = [
        _round2(sum(diff for idx, diff in enumerate(diffs) if idx != omitted) / (len(diffs) - 1))
        for omitted in range(len(diffs))
    ]
    return SensitivityAnalysisResult(
        name="leave_one_pair_out",
        method="Paired-period estimate after omitting one A/B pair at a time",
        ci_lower=min(leave_one_estimates),
        ci_upper=max(leave_one_estimates),
        n_used_a=len(diffs),
        n_used_b=len(diffs),
        summary=(
            "Leave-one-pair estimates ranged from "
            f"{min(leave_one_estimates):+.2f} to {max(leave_one_estimates):+.2f}."
        ),
    )


def _compute_secondary_outcomes(
    observations: list[Observation],
    protocol: AnalysisProtocol,
) -> list[SecondaryOutcomeResult]:
    results: list[SecondaryOutcomeResult] = []
    for outcome in protocol.secondary_outcomes:
        scores_a = [
            obs.secondary_scores[outcome.id]
            for obs in observations
            if obs.condition == "A" and outcome.id in obs.secondary_scores
        ]
        scores_b = [
            obs.secondary_scores[outcome.id]
            for obs in observations
            if obs.condition == "B" and outcome.id in obs.secondary_scores
        ]
        mean_a = sum(scores_a) / len(scores_a) if scores_a else None
        mean_b = sum(scores_b) / len(scores_b) if scores_b else None
        diff = mean_a - mean_b if mean_a is not None and mean_b is not None else None
        summary = _secondary_summary(outcome.label, mean_a, mean_b, diff)
        results.append(
            SecondaryOutcomeResult(
                outcome_id=outcome.id,
                label=outcome.label,
                mean_a=_round2(mean_a) if mean_a is not None else None,
                mean_b=_round2(mean_b) if mean_b is not None else None,
                difference=_round2(diff) if diff is not None else None,
                n_used_a=len(scores_a),
                n_used_b=len(scores_b),
                summary=summary,
            )
        )
    return results


def _secondary_summary(
    label: str,
    mean_a: float | None,
    mean_b: float | None,
    diff: float | None,
) -> str:
    if mean_a is None or mean_b is None or diff is None:
        return f"{label}: not enough secondary outcome data for both conditions."
    direction = "higher on A" if diff > 0 else "higher on B" if diff < 0 else "similar"
    return (
        f"{label}: {direction} descriptively; secondary outcomes do not change the primary verdict."
    )


def _count_adverse_events(observations: list[Observation]) -> dict[str, int]:
    counts = {severity.value: 0 for severity in AdverseEventSeverity}
    for obs in observations:
        if obs.adverse_event_severity is not None or obs.irritation == "yes":
            severity = (
                obs.adverse_event_severity.value
                if obs.adverse_event_severity is not None
                else AdverseEventSeverity.MILD.value
            )
            counts[severity] = counts.get(severity, 0) + 1
    return {severity: count for severity, count in counts.items() if count > 0}


def _harm_benefit_summary(adverse_event_by_severity: dict[str, int]) -> str:
    if not adverse_event_by_severity:
        return "No adverse events or discomfort were recorded."
    parts = [f"{count} {severity}" for severity, count in sorted(adverse_event_by_severity.items())]
    return "Adverse events or discomfort recorded: " + ", ".join(parts) + "."


def _reliability_warnings(observations: list[Observation]) -> list[str]:
    scores = [obs.primary_score for obs in observations if obs.primary_score is not None]
    warnings: list[str] = []
    if len(scores) < 4:
        return warnings
    distinct = len(set(scores))
    if distinct <= 2:
        warnings.append(
            "Primary scores used only one or two distinct values; "
            "range compression may hide signal."
        )
    if min(scores) == 0 or max(scores) == 10:
        edge_count = sum(1 for score in scores if score in {0, 10})
        if edge_count / len(scores) >= 0.25:
            warnings.append(
                "Many scores are at the 0 or 10 edge; ceiling/floor effects are possible."
            )
    repeated_runs = _longest_identical_run(scores)
    if repeated_runs >= 5:
        warnings.append(
            f"{repeated_runs} identical scores appeared consecutively; check rating consistency."
        )
    return warnings


def _longest_identical_run(values: list[float]) -> int:
    longest = 0
    current = 0
    previous: float | None = None
    for value in values:
        if value == previous:
            current += 1
        else:
            current = 1
            previous = value
        longest = max(longest, current)
    return longest


def _time_trend_warnings(observations: list[Observation]) -> list[str]:
    scored = [obs for obs in observations if obs.primary_score is not None]
    if len(scored) < 6:
        return []
    xs = [float(obs.day_index) for obs in scored]
    ys = [float(obs.primary_score) for obs in scored if obs.primary_score is not None]
    corr = _pearson(xs, ys)
    if abs(corr) >= 0.55:
        direction = "improved" if corr > 0 else "declined"
        return [
            f"Scores {direction} across calendar time; time trend may confound condition effects."
        ]
    return []


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denom_x == 0 or denom_y == 0:
        return 0.0
    return numerator / (denom_x * denom_y)


def _carryover_warnings(
    observations: list[Observation],
    protocol: AnalysisProtocol,
) -> list[str]:
    scored = [obs for obs in observations if obs.primary_score is not None]
    if len(scored) < 8:
        return []
    first_after_switch: list[float] = []
    later_in_block: list[float] = []
    for obs in scored:
        block_day = ((obs.day_index - 1) % protocol.block_length_days) + 1
        assert obs.primary_score is not None
        if block_day <= min(2, protocol.block_length_days):
            first_after_switch.append(obs.primary_score)
        else:
            later_in_block.append(obs.primary_score)
    if len(first_after_switch) < 2 or len(later_in_block) < 2:
        return []
    first_mean = sum(first_after_switch) / len(first_after_switch)
    later_mean = sum(later_in_block) / len(later_in_block)
    if abs(first_mean - later_mean) >= protocol.minimum_meaningful_difference:
        return [
            "Scores differ meaningfully between early-switch days and later block days; "
            "carryover or adaptation is possible."
        ]
    return []


def _actionability(
    grade: QualityGrade,
    verdict: Verdict,
    meets_minimum: bool,
    supports_no_meaningful_difference: bool,
    adverse_event_by_severity: dict[str, int],
    early_stop: bool,
) -> ActionabilityClass:
    if adverse_event_by_severity.get("severe", 0) > 0 or (
        early_stop and sum(adverse_event_by_severity.values()) > 0
    ):
        return ActionabilityClass.STOP_FOR_SAFETY
    if grade == QualityGrade.D:
        return ActionabilityClass.INSUFFICIENT_DATA
    if supports_no_meaningful_difference:
        return ActionabilityClass.INCONCLUSIVE_NO_ACTION
    if verdict == "inconclusive" or not meets_minimum:
        return ActionabilityClass.REPEAT_WITH_BETTER_CONTROLS
    if verdict == "favors_a":
        return ActionabilityClass.KEEP_CURRENT
    return ActionabilityClass.SWITCH


# ---------------------------------------------------------------------------
# Improvement #7: Sample-size imbalance warning
# ---------------------------------------------------------------------------


def _check_imbalance(n_a: int, n_b: int) -> str | None:
    if n_a == 0 or n_b == 0:
        return None
    ratio = max(n_a, n_b) / min(n_a, n_b)
    if ratio >= 1.5:
        smaller = "B" if n_a > n_b else "A"
        pct = round((1 - min(n_a, n_b) / max(n_a, n_b)) * 100)
        return f"Condition {smaller} had {pct}% fewer usable days; interpret with caution."
    return None


# ---------------------------------------------------------------------------
# Improvement #9: Underpowered / wide-CI warning
# ---------------------------------------------------------------------------


def _check_underpowered(
    difference: float,
    ci_lower: float,
    ci_upper: float,
) -> str | None:
    ci_width = abs(ci_upper - ci_lower)
    abs_diff = abs(difference)
    if abs_diff > 0 and ci_width / abs_diff > 1.0:
        return "Wide confidence interval relative to effect size; low statistical power."
    return None


# ---------------------------------------------------------------------------
# Summary and caveats generation
# ---------------------------------------------------------------------------


def _generate_summary(
    mean_a: float,
    mean_b: float,
    difference: float,
    ci_lower: float,
    ci_upper: float,
    grade: QualityGrade,
    early_stop: bool,
    cohens_d: float | None,
    verdict: Verdict,
    analysis_method: AnalysisMethod,
    supports_no_meaningful_difference: bool,
) -> str:
    if grade == QualityGrade.D:
        return "Insufficient data for reliable inference."

    direction_text = {
        "favors_a": "favors Condition A",
        "favors_b": "favors Condition B",
        "inconclusive": "inconclusive",
    }[verdict]

    grade_desc = {
        QualityGrade.A: "strong",
        QualityGrade.B: "good",
        QualityGrade.C: "limited",
        QualityGrade.D: "insufficient",
    }

    method_text = (
        "paired-period estimate"
        if analysis_method == AnalysisMethod.PAIRED_BLOCKS
        else "daily-score Welch estimate"
    )
    parts = [
        f"Mean A: {mean_a:.2f}, Mean B: {mean_b:.2f}, difference: {difference:+.2f}.",
        f"95% CI: [{ci_lower:.2f}, {ci_upper:.2f}].",
        f"Primary method: {method_text}.",
        f"Result {direction_text} with {grade_desc[grade]} evidence (Grade {grade.value}).",
    ]
    if supports_no_meaningful_difference:
        parts.append("The confidence interval fits within the meaningful-change margin.")
    if cohens_d is not None:
        size_label = _cohens_d_label(cohens_d)
        parts.append(f"Effect size: Cohen's d = {cohens_d:+.2f} ({size_label}).")
    if early_stop:
        parts.append("Trial stopped early; interpret with caution.")
    return " ".join(parts)


def _cohens_d_label(d: float) -> str:
    ad = abs(d)
    if ad < 0.2:
        return "negligible"
    if ad < 0.5:
        return "small"
    if ad < 0.8:
        return "medium"
    return "large"


def _generate_caveats(
    early_stop: bool,
    observations: list[Observation],
    late_backfill_excluded: int,
    imbalance_warning: str | None,
    underpowered_warning: str | None,
    planned_days_defaulted: bool,
    data_warnings: list[str],
) -> str:
    caveats = ["Unblinded self-report; expectancy effects possible."]
    if early_stop:
        has_irritation = any(o.irritation == "yes" for o in observations)
        if has_irritation:
            caveats.append("Early termination due to persistent irritation.")
        else:
            caveats.append("Early termination.")
    if late_backfill_excluded > 0:
        caveats.append(f"{late_backfill_excluded} late-backfill day(s) excluded from analysis.")
    if imbalance_warning:
        caveats.append(imbalance_warning)
    if underpowered_warning:
        caveats.append(underpowered_warning)
    if planned_days_defaulted:
        caveats.append(f"planned_days missing from protocol; defaulted to {_PLANNED_DAYS_DEFAULT}.")
    caveats.extend(data_warnings)
    return " ".join(caveats)

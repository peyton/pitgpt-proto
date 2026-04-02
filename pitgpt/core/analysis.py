import math
from decimal import ROUND_HALF_UP, Decimal

from scipy import stats

from pitgpt.core.models import (
    BlockBreakdown,
    Observation,
    QualityGrade,
    ResultCard,
    SensitivityResult,
    Verdict,
)

_PLANNED_DAYS_DEFAULT = 42


def analyze(protocol: dict, observations: list[Observation]) -> ResultCard:
    planned_days_defaulted = "planned_days" not in protocol
    planned_days = protocol.get("planned_days", _PLANNED_DAYS_DEFAULT)

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

    if len(scores_a) < 2 or len(scores_b) < 2:
        caveats_parts = ["Too few usable observations to compute effect size."]
        if planned_days_defaulted:
            caveats_parts.append(
                f"planned_days missing from protocol; defaulted to {_PLANNED_DAYS_DEFAULT}."
            )
        return ResultCard(
            quality_grade=QualityGrade.D,
            verdict="insufficient_data",
            n_used_a=len(scores_a),
            n_used_b=len(scores_b),
            adherence_rate=_round4(adherence_rate),
            days_logged_pct=_round4(days_logged_pct),
            early_stop=early_stop,
            late_backfill_excluded=late_backfill_excluded,
            planned_days_defaulted=planned_days_defaulted,
            summary="Insufficient data for reliable inference.",
            caveats=" ".join(caveats_parts),
        )

    mean_a = sum(scores_a) / len(scores_a)
    mean_b = sum(scores_b) / len(scores_b)
    raw_diff = mean_a - mean_b
    difference = _round2(raw_diff)

    t_stat, _p_value = stats.ttest_ind(scores_a, scores_b, equal_var=False)
    se = abs(raw_diff / t_stat) if t_stat != 0 else 0.0
    df = _welch_df(scores_a, scores_b)
    t_crit = stats.t.ppf(0.975, df) if df > 0 else 1.96
    margin = se * t_crit
    ci_lower = _round2(raw_diff - margin)
    ci_upper = _round2(raw_diff + margin)

    cohens_d = _compute_cohens_d(scores_a, scores_b)
    verdict = _compute_verdict(difference, ci_lower, ci_upper)

    grade = _compute_grade(adherence_rate, days_logged_pct, early_stop, planned_days, observations)

    block_breakdown = _compute_block_breakdown(filtered, protocol)
    sensitivity = _compute_sensitivity(observations)

    imbalance_warning = _check_imbalance(len(scores_a), len(scores_b))
    underpowered_warning = _check_underpowered(difference, ci_lower, ci_upper)

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
    )
    caveats = _generate_caveats(
        early_stop,
        observations,
        late_backfill_excluded,
        imbalance_warning,
        underpowered_warning,
        planned_days_defaulted,
    )

    return ResultCard(
        quality_grade=grade,
        verdict=verdict,
        mean_a=_round2(mean_a),
        mean_b=_round2(mean_b),
        difference=difference,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        cohens_d=cohens_d,
        n_used_a=len(scores_a),
        n_used_b=len(scores_b),
        adherence_rate=_round4(adherence_rate),
        days_logged_pct=_round4(days_logged_pct),
        early_stop=early_stop,
        late_backfill_excluded=late_backfill_excluded,
        block_breakdown=block_breakdown,
        sensitivity_excluding_partial=sensitivity,
        planned_days_defaulted=planned_days_defaulted,
        summary=summary,
        caveats=caveats,
    )


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


def _compute_grade(
    adherence_rate: float,
    days_logged_pct: float,
    early_stop: bool,
    planned_days: int,
    observations: list[Observation],
) -> QualityGrade:
    if adherence_rate < 0.50 or days_logged_pct < 0.50:
        return QualityGrade.D

    if early_stop:
        if adherence_rate >= 0.70 and days_logged_pct >= 0.75:
            return QualityGrade.C
        if adherence_rate < 0.50 or days_logged_pct < 0.50:
            return QualityGrade.D
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


# ---------------------------------------------------------------------------
# Improvement #3: Explicit verdict
# ---------------------------------------------------------------------------


def _compute_verdict(difference: float, ci_lower: float, ci_upper: float) -> Verdict:
    if ci_lower <= 0 <= ci_upper:
        return "inconclusive"
    if difference > 0:
        return "favors_a"
    return "favors_b"


# ---------------------------------------------------------------------------
# Improvement #5: Per-block breakdown
# ---------------------------------------------------------------------------


def _compute_block_breakdown(
    filtered: list[Observation],
    protocol: dict,
) -> list[BlockBreakdown]:
    block_length = protocol.get("block_length_days", 7)
    if block_length <= 0:
        return []

    blocks: dict[tuple[int, str], list[float]] = {}
    for o in filtered:
        if o.primary_score is None:
            continue
        block_idx = (o.day_index - 1) // block_length
        key = (block_idx, o.condition)
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

    t_stat, _ = stats.ttest_ind(sa, sb, equal_var=False)
    se = abs(diff / t_stat) if t_stat != 0 else 0.0
    df = _welch_df(sa, sb)
    t_crit = stats.t.ppf(0.975, df) if df > 0 else 1.96
    margin = se * t_crit

    return SensitivityResult(
        difference=diff,
        ci_lower=_round2(diff - margin),
        ci_upper=_round2(diff + margin),
        n_used_a=len(sa),
        n_used_b=len(sb),
    )


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

    parts = [
        f"Mean A: {mean_a:.2f}, Mean B: {mean_b:.2f}, difference: {difference:+.2f}.",
        f"95% CI: [{ci_lower:.2f}, {ci_upper:.2f}].",
        f"Result {direction_text} with {grade_desc[grade]} evidence (Grade {grade.value}).",
    ]
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
    return " ".join(caveats)

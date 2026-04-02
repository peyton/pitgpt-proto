from scipy import stats

from pitgpt.core.models import Observation, QualityGrade, ResultCard


def analyze(protocol: dict, observations: list[Observation]) -> ResultCard:
    planned_days = protocol.get("planned_days", 42)

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

    days_logged_pct = scored_not_late_backfill / denom if denom > 0 else 0.0
    adherence_rate = fully_adherent / denom if denom > 0 else 0.0

    if len(scores_a) < 2 or len(scores_b) < 2:
        return ResultCard(
            quality_grade=QualityGrade.D,
            n_used_a=len(scores_a),
            n_used_b=len(scores_b),
            adherence_rate=round(adherence_rate, 4),
            days_logged_pct=round(days_logged_pct, 4),
            early_stop=early_stop,
            summary="Insufficient data for reliable inference.",
            caveats="Too few usable observations to compute effect size.",
        )

    mean_a = sum(scores_a) / len(scores_a)
    mean_b = sum(scores_b) / len(scores_b)
    difference = round(mean_a - mean_b, 2)

    t_stat, p_value = stats.ttest_ind(scores_a, scores_b, equal_var=False)
    se = abs(difference / t_stat) if t_stat != 0 else 0.0
    df = _welch_df(scores_a, scores_b)
    t_crit = stats.t.ppf(0.975, df) if df > 0 else 1.96
    margin = se * t_crit
    ci_lower = round(difference - margin, 2)
    ci_upper = round(difference + margin, 2)

    grade = _compute_grade(adherence_rate, days_logged_pct, early_stop, planned_days, observations)

    summary = _generate_summary(mean_a, mean_b, difference, ci_lower, ci_upper, grade, early_stop)
    caveats = _generate_caveats(early_stop, observations)

    return ResultCard(
        quality_grade=grade,
        mean_a=round(mean_a, 2),
        mean_b=round(mean_b, 2),
        difference=difference,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        n_used_a=len(scores_a),
        n_used_b=len(scores_b),
        adherence_rate=round(adherence_rate, 4),
        days_logged_pct=round(days_logged_pct, 4),
        early_stop=early_stop,
        summary=summary,
        caveats=caveats,
    )


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


def _generate_summary(
    mean_a: float,
    mean_b: float,
    difference: float,
    ci_lower: float,
    ci_upper: float,
    grade: QualityGrade,
    early_stop: bool,
) -> str:
    if grade == QualityGrade.D:
        return "Insufficient data for reliable inference."

    if ci_lower <= 0 <= ci_upper:
        direction = "inconclusive"
    elif difference > 0:
        direction = "favors Condition A"
    else:
        direction = "favors Condition B"

    grade_desc = {
        QualityGrade.A: "strong",
        QualityGrade.B: "good",
        QualityGrade.C: "limited",
        QualityGrade.D: "insufficient",
    }

    parts = [
        f"Mean A: {mean_a:.2f}, Mean B: {mean_b:.2f}, difference: {difference:+.2f}.",
        f"95% CI: [{ci_lower:.2f}, {ci_upper:.2f}].",
        f"Result {direction} with {grade_desc[grade]} evidence (Grade {grade.value}).",
    ]
    if early_stop:
        parts.append("Trial stopped early; interpret with caution.")
    return " ".join(parts)


def _generate_caveats(early_stop: bool, observations: list[Observation]) -> str:
    caveats = ["Unblinded self-report; expectancy effects possible."]
    if early_stop:
        has_irritation = any(o.irritation == "yes" for o in observations)
        if has_irritation:
            caveats.append("Early termination due to persistent irritation.")
        else:
            caveats.append("Early termination.")
    backfilled = sum(
        1
        for o in observations
        if o.is_backfill == "yes" and o.backfill_days is not None and o.backfill_days > 2
    )
    if backfilled > 0:
        caveats.append(f"{backfilled} late-backfill day(s) excluded from analysis.")
    return " ".join(caveats)

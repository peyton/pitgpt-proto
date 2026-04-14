use std::collections::{BTreeMap, BTreeSet};

use serde_json::Value;
use statrs::distribution::{ContinuousCDF, StudentsT};

use crate::models::{
    Adherence, AnalysisMethod, AnalysisProtocol, BlockBreakdown, Condition, Observation,
    PairedBlockEstimate, QualityGrade, ResultCard, SensitivityResult, Verdict, YesNo,
};

pub fn analyze_result(
    protocol_value: Value,
    observations: Vec<Observation>,
) -> Result<ResultCard, String> {
    let planned_days_defaulted = AnalysisProtocol::planned_days_defaulted(&protocol_value);
    let protocol: AnalysisProtocol = serde_json::from_value(protocol_value)
        .map_err(|err| format!("invalid analysis protocol: {err}"))?;
    if protocol.planned_days == 0 {
        return Err("planned_days must be positive".to_string());
    }
    if protocol.block_length_days == 0 {
        return Err("block_length_days must be positive".to_string());
    }

    let data_warnings = validate_observations(&observations, &protocol);
    let early_stop = detect_early_stop(&observations, protocol.planned_days);
    let denom = if early_stop && !observations.is_empty() {
        observations
            .iter()
            .map(|obs| obs.day_index)
            .max()
            .unwrap_or(protocol.planned_days)
    } else {
        protocol.planned_days
    } as f64;

    let filtered = filter_observations(&observations);
    let scores_a = scores_for_condition(&filtered, Condition::A);
    let scores_b = scores_for_condition(&filtered, Condition::B);

    let scored_not_late_backfill = observations
        .iter()
        .filter(|obs| {
            obs.primary_score.is_some()
                && !(obs.is_backfill == YesNo::Yes
                    && obs.backfill_days.is_some_and(|days| days > 2.0))
        })
        .count();
    let fully_adherent = observations
        .iter()
        .filter(|obs| obs.adherence == Adherence::Yes)
        .count();
    let late_backfill_excluded = observations
        .iter()
        .filter(|obs| {
            obs.is_backfill == YesNo::Yes && obs.backfill_days.is_some_and(|days| days > 2.0)
        })
        .count();

    let days_logged_pct = if denom > 0.0 {
        scored_not_late_backfill as f64 / denom
    } else {
        0.0
    };
    let adherence_rate = if denom > 0.0 {
        fully_adherent as f64 / denom
    } else {
        0.0
    };

    if scores_a.len() < 2 || scores_b.len() < 2 {
        let mut caveats_parts =
            vec!["Too few usable observations to compute effect size.".to_string()];
        if planned_days_defaulted {
            caveats_parts.push("planned_days missing from protocol; defaulted to 42.".to_string());
        }
        caveats_parts.extend(data_warnings.clone());
        return Ok(ResultCard {
            quality_grade: QualityGrade::D,
            verdict: Verdict::InsufficientData,
            analysis_method: AnalysisMethod::InsufficientData,
            mean_a: None,
            mean_b: None,
            difference: None,
            ci_lower: None,
            ci_upper: None,
            cohens_d: None,
            paired_block: None,
            n_used_a: scores_a.len(),
            n_used_b: scores_b.len(),
            adherence_rate: round4(adherence_rate),
            days_logged_pct: round4(days_logged_pct),
            early_stop,
            late_backfill_excluded,
            block_breakdown: vec![],
            sensitivity_excluding_partial: None,
            planned_days_defaulted,
            minimum_meaningful_difference: protocol.minimum_meaningful_difference,
            meets_minimum_meaningful_effect: None,
            data_warnings,
            summary: "Insufficient data for reliable inference.".to_string(),
            caveats: caveats_parts.join(" "),
        });
    }

    let mean_a = mean(&scores_a);
    let mean_b = mean(&scores_b);
    let raw_diff = mean_a - mean_b;
    let difference = round2(raw_diff);
    let (ci_lower, ci_upper) = welch_ci(&scores_a, &scores_b, raw_diff);
    let cohens_d = compute_cohens_d(&scores_a, &scores_b);
    let verdict = compute_verdict(difference, ci_lower, ci_upper);
    let meets_minimum = difference.abs() >= protocol.minimum_meaningful_difference;
    let grade = compute_grade(adherence_rate, days_logged_pct, early_stop);
    let block_breakdown = compute_block_breakdown(&filtered, &protocol);
    let paired_block = compute_paired_block_estimate(&block_breakdown);
    let sensitivity = compute_sensitivity(&observations);
    let imbalance_warning = check_imbalance(scores_a.len(), scores_b.len());
    let underpowered_warning = check_underpowered(difference, ci_lower, ci_upper);
    let summary = generate_summary(SummaryInputs {
        mean_a,
        mean_b,
        difference,
        ci_lower,
        ci_upper,
        grade,
        early_stop,
        cohens_d,
        verdict,
    });
    let caveats = generate_caveats(
        early_stop,
        &observations,
        late_backfill_excluded,
        imbalance_warning,
        underpowered_warning,
        planned_days_defaulted,
        &data_warnings,
    );

    Ok(ResultCard {
        quality_grade: grade,
        verdict,
        analysis_method: if paired_block
            .as_ref()
            .and_then(|estimate| estimate.difference)
            .is_some()
        {
            AnalysisMethod::PairedBlocks
        } else {
            AnalysisMethod::Welch
        },
        mean_a: Some(round2(mean_a)),
        mean_b: Some(round2(mean_b)),
        difference: Some(difference),
        ci_lower: Some(ci_lower),
        ci_upper: Some(ci_upper),
        cohens_d,
        paired_block,
        n_used_a: scores_a.len(),
        n_used_b: scores_b.len(),
        adherence_rate: round4(adherence_rate),
        days_logged_pct: round4(days_logged_pct),
        early_stop,
        late_backfill_excluded,
        block_breakdown,
        sensitivity_excluding_partial: sensitivity,
        planned_days_defaulted,
        minimum_meaningful_difference: protocol.minimum_meaningful_difference,
        meets_minimum_meaningful_effect: Some(meets_minimum),
        data_warnings,
        summary,
        caveats,
    })
}

fn validate_observations(observations: &[Observation], protocol: &AnalysisProtocol) -> Vec<String> {
    let mut warnings = Vec::new();
    if observations.is_empty() {
        return warnings;
    }

    let days: Vec<u32> = observations.iter().map(|obs| obs.day_index).collect();
    let dates: Vec<String> = observations
        .iter()
        .filter(|obs| !obs.date.is_empty())
        .map(|obs| obs.date.clone())
        .collect();

    let duplicate_days = duplicates(&days);
    if !duplicate_days.is_empty() {
        warnings.push(format!(
            "Duplicate day_index value(s): {}.",
            duplicate_days
                .iter()
                .map(u32::to_string)
                .collect::<Vec<_>>()
                .join(", ")
        ));
    }

    let duplicate_dates = duplicates(&dates);
    if !duplicate_dates.is_empty() {
        warnings.push(format!(
            "Duplicate date value(s): {}.",
            duplicate_dates.join(", ")
        ));
    }

    if !days.windows(2).all(|pair| pair[0] <= pair[1]) {
        warnings.push("Observations are not sorted by day_index.".to_string());
    }
    if !dates.windows(2).all(|pair| pair[0] <= pair[1]) {
        warnings.push("Observations are not sorted by date.".to_string());
    }

    let max_day = days.iter().copied().max().unwrap_or(0);
    let expected_days: BTreeSet<u32> = (1..=max_day.min(protocol.planned_days)).collect();
    let observed_days: BTreeSet<u32> = days.iter().copied().collect();
    let missing_days: Vec<u32> = expected_days.difference(&observed_days).copied().collect();
    if !missing_days.is_empty() {
        let preview = missing_days
            .iter()
            .take(5)
            .map(u32::to_string)
            .collect::<Vec<_>>()
            .join(", ");
        let suffix = if missing_days.len() > 5 { "..." } else { "" };
        warnings.push(format!("Missing day_index value(s): {preview}{suffix}."));
    }

    let usable = filter_observations(observations);
    let n_a = scores_for_condition(&usable, Condition::A).len();
    let n_b = scores_for_condition(&usable, Condition::B).len();
    if n_a == 0 || n_b == 0 {
        warnings.push("Both conditions need usable scored observations.".to_string());
    } else if n_a.max(n_b) as f64 / n_a.min(n_b) as f64 >= 2.0 {
        warnings.push("Usable observations are highly imbalanced between conditions.".to_string());
    }

    warnings
}

fn duplicates<T>(values: &[T]) -> Vec<T>
where
    T: Ord + Clone,
{
    let mut counts = BTreeMap::<T, usize>::new();
    for value in values {
        *counts.entry(value.clone()).or_default() += 1;
    }
    counts
        .into_iter()
        .filter_map(|(value, count)| (count > 1).then_some(value))
        .collect()
}

fn filter_observations(observations: &[Observation]) -> Vec<Observation> {
    observations
        .iter()
        .filter(|obs| obs.adherence != Adherence::No)
        .filter(|obs| {
            !(obs.is_backfill == YesNo::Yes && obs.backfill_days.is_some_and(|days| days > 2.0))
        })
        .cloned()
        .collect()
}

fn detect_early_stop(observations: &[Observation], planned_days: u32) -> bool {
    observations
        .iter()
        .map(|obs| obs.day_index)
        .max()
        .is_some_and(|max_day| max_day < planned_days)
}

fn scores_for_condition(observations: &[Observation], condition: Condition) -> Vec<f64> {
    observations
        .iter()
        .filter(|obs| obs.condition == condition)
        .filter_map(|obs| obs.primary_score)
        .collect()
}

fn mean(values: &[f64]) -> f64 {
    values.iter().sum::<f64>() / values.len() as f64
}

fn sample_variance(values: &[f64]) -> f64 {
    let n = values.len();
    if n < 2 {
        return 0.0;
    }
    let avg = mean(values);
    values
        .iter()
        .map(|value| (value - avg).powi(2))
        .sum::<f64>()
        / (n - 1) as f64
}

fn welch_df(a: &[f64], b: &[f64]) -> f64 {
    let na = a.len() as f64;
    let nb = b.len() as f64;
    let va = sample_variance(a);
    let vb = sample_variance(b);
    let num = (va / na + vb / nb).powi(2);
    let denom = (va / na).powi(2) / (na - 1.0) + (vb / nb).powi(2) / (nb - 1.0);
    if denom == 0.0 {
        1.0
    } else {
        num / denom
    }
}

fn welch_ci(a: &[f64], b: &[f64], raw_diff: f64) -> (f64, f64) {
    let na = a.len() as f64;
    let nb = b.len() as f64;
    let va = sample_variance(a);
    let vb = sample_variance(b);
    let se = (va / na + vb / nb).sqrt();
    if se == 0.0 {
        let rounded = round2(raw_diff);
        return (rounded, rounded);
    }
    let df = welch_df(a, b);
    let t_crit = StudentsT::new(0.0, 1.0, df)
        .map(|dist| dist.inverse_cdf(0.975))
        .unwrap_or(1.96);
    let margin = se * t_crit;
    (round2(raw_diff - margin), round2(raw_diff + margin))
}

fn compute_cohens_d(a: &[f64], b: &[f64]) -> Option<f64> {
    if a.len() < 2 || b.len() < 2 {
        return None;
    }
    let na = a.len() as f64;
    let nb = b.len() as f64;
    let va = sample_variance(a);
    let vb = sample_variance(b);
    let pooled_sd = (((na - 1.0) * va + (nb - 1.0) * vb) / (na + nb - 2.0)).sqrt();
    if pooled_sd == 0.0 {
        Some(0.0)
    } else {
        Some(round2((mean(a) - mean(b)) / pooled_sd))
    }
}

fn compute_verdict(difference: f64, ci_lower: f64, ci_upper: f64) -> Verdict {
    if ci_lower <= 0.0 && ci_upper >= 0.0 {
        Verdict::Inconclusive
    } else if difference > 0.0 {
        Verdict::FavorsA
    } else {
        Verdict::FavorsB
    }
}

fn compute_grade(adherence_rate: f64, days_logged_pct: f64, early_stop: bool) -> QualityGrade {
    if adherence_rate < 0.50 || days_logged_pct < 0.50 {
        return QualityGrade::D;
    }
    if early_stop {
        return QualityGrade::C;
    }
    if adherence_rate >= 0.85 && days_logged_pct >= 0.90 {
        QualityGrade::A
    } else if adherence_rate >= 0.70 && days_logged_pct >= 0.75 {
        QualityGrade::B
    } else {
        QualityGrade::C
    }
}

fn compute_block_breakdown(
    filtered: &[Observation],
    protocol: &AnalysisProtocol,
) -> Vec<BlockBreakdown> {
    let mut blocks = BTreeMap::<(u32, String), Vec<f64>>::new();
    for obs in filtered {
        let Some(score) = obs.primary_score else {
            continue;
        };
        let block_index = (obs.day_index - 1) / protocol.block_length_days;
        let condition = match obs.condition {
            Condition::A => "A",
            Condition::B => "B",
        }
        .to_string();
        blocks
            .entry((block_index, condition))
            .or_default()
            .push(score);
    }
    blocks
        .into_iter()
        .map(|((block_index, condition), vals)| BlockBreakdown {
            block_index,
            condition,
            mean: round2(mean(&vals)),
            n: vals.len(),
        })
        .collect()
}

fn compute_paired_block_estimate(
    block_breakdown: &[BlockBreakdown],
) -> Option<PairedBlockEstimate> {
    let mut by_pair = BTreeMap::<u32, BTreeMap<String, f64>>::new();
    for block in block_breakdown {
        let pair_index = block.block_index / 2;
        by_pair
            .entry(pair_index)
            .or_default()
            .insert(block.condition.clone(), block.mean);
    }

    let paired_diffs: Vec<f64> = by_pair
        .values()
        .filter_map(|pair| Some(pair.get("A")? - pair.get("B")?))
        .collect();
    if paired_diffs.is_empty() {
        return None;
    }
    if paired_diffs.len() < 2 {
        return Some(PairedBlockEstimate {
            difference: Some(round2(paired_diffs[0])),
            ci_lower: None,
            ci_upper: None,
            n_pairs: paired_diffs.len(),
        });
    }

    let mean_diff = mean(&paired_diffs);
    let variance = sample_variance(&paired_diffs);
    let se = (variance / paired_diffs.len() as f64).sqrt();
    let (ci_lower, ci_upper) = if se == 0.0 {
        (round2(mean_diff), round2(mean_diff))
    } else {
        let df = paired_diffs.len() as f64 - 1.0;
        let t_crit = StudentsT::new(0.0, 1.0, df)
            .map(|dist| dist.inverse_cdf(0.975))
            .unwrap_or(1.96);
        let margin = se * t_crit;
        (round2(mean_diff - margin), round2(mean_diff + margin))
    };

    Some(PairedBlockEstimate {
        difference: Some(round2(mean_diff)),
        ci_lower: Some(ci_lower),
        ci_upper: Some(ci_upper),
        n_pairs: paired_diffs.len(),
    })
}

fn compute_sensitivity(observations: &[Observation]) -> Option<SensitivityResult> {
    if !observations
        .iter()
        .any(|obs| obs.adherence == Adherence::Partial)
    {
        return None;
    }
    let strict: Vec<Observation> = observations
        .iter()
        .filter(|obs| obs.adherence == Adherence::Yes)
        .filter(|obs| {
            !(obs.is_backfill == YesNo::Yes && obs.backfill_days.is_some_and(|days| days > 2.0))
        })
        .cloned()
        .collect();
    let scores_a = scores_for_condition(&strict, Condition::A);
    let scores_b = scores_for_condition(&strict, Condition::B);
    if scores_a.len() < 2 || scores_b.len() < 2 {
        return Some(SensitivityResult {
            difference: None,
            ci_lower: None,
            ci_upper: None,
            n_used_a: scores_a.len(),
            n_used_b: scores_b.len(),
        });
    }
    let raw_diff = mean(&scores_a) - mean(&scores_b);
    let (ci_lower, ci_upper) = welch_ci(&scores_a, &scores_b, raw_diff);
    Some(SensitivityResult {
        difference: Some(round2(raw_diff)),
        ci_lower: Some(ci_lower),
        ci_upper: Some(ci_upper),
        n_used_a: scores_a.len(),
        n_used_b: scores_b.len(),
    })
}

fn check_imbalance(n_a: usize, n_b: usize) -> Option<String> {
    if n_a == 0 || n_b == 0 {
        return None;
    }
    let ratio = n_a.max(n_b) as f64 / n_a.min(n_b) as f64;
    if ratio >= 1.5 {
        let smaller = if n_a > n_b { "B" } else { "A" };
        let pct = ((1.0 - n_a.min(n_b) as f64 / n_a.max(n_b) as f64) * 100.0).round();
        Some(format!(
            "Condition {smaller} had {pct:.0}% fewer usable days; interpret with caution."
        ))
    } else {
        None
    }
}

fn check_underpowered(difference: f64, ci_lower: f64, ci_upper: f64) -> Option<String> {
    let ci_width = (ci_upper - ci_lower).abs();
    let abs_diff = difference.abs();
    if abs_diff > 0.0 && ci_width / abs_diff > 1.0 {
        Some("Wide confidence interval relative to effect size; low statistical power.".to_string())
    } else {
        None
    }
}

struct SummaryInputs {
    mean_a: f64,
    mean_b: f64,
    difference: f64,
    ci_lower: f64,
    ci_upper: f64,
    grade: QualityGrade,
    early_stop: bool,
    cohens_d: Option<f64>,
    verdict: Verdict,
}

fn generate_summary(inputs: SummaryInputs) -> String {
    let SummaryInputs {
        mean_a,
        mean_b,
        difference,
        ci_lower,
        ci_upper,
        grade,
        early_stop,
        cohens_d,
        verdict,
    } = inputs;
    if grade == QualityGrade::D {
        return "Insufficient data for reliable inference.".to_string();
    }
    let direction_text = match verdict {
        Verdict::FavorsA => "favors Condition A",
        Verdict::FavorsB => "favors Condition B",
        Verdict::Inconclusive => "inconclusive",
        Verdict::InsufficientData => "insufficient data",
    };
    let grade_desc = match grade {
        QualityGrade::A => "strong",
        QualityGrade::B => "good",
        QualityGrade::C => "limited",
        QualityGrade::D => "insufficient",
    };
    let mut parts = vec![
        format!(
            "Mean A: {:.2}, Mean B: {:.2}, difference: {:+.2}.",
            mean_a, mean_b, difference
        ),
        format!("95% CI: [{:.2}, {:.2}].", ci_lower, ci_upper),
        format!(
            "Result {direction_text} with {grade_desc} evidence (Grade {:?}).",
            grade
        ),
    ];
    if let Some(d) = cohens_d {
        parts.push(format!(
            "Effect size: Cohen's d = {:+.2} ({}).",
            d,
            cohens_d_label(d)
        ));
    }
    if early_stop {
        parts.push("Trial stopped early; interpret with caution.".to_string());
    }
    parts.join(" ")
}

fn cohens_d_label(d: f64) -> &'static str {
    let ad = d.abs();
    if ad < 0.2 {
        "negligible"
    } else if ad < 0.5 {
        "small"
    } else if ad < 0.8 {
        "medium"
    } else {
        "large"
    }
}

fn generate_caveats(
    early_stop: bool,
    observations: &[Observation],
    late_backfill_excluded: usize,
    imbalance_warning: Option<String>,
    underpowered_warning: Option<String>,
    planned_days_defaulted: bool,
    data_warnings: &[String],
) -> String {
    let mut caveats = vec!["Unblinded self-report; expectancy effects possible.".to_string()];
    if early_stop {
        if observations.iter().any(|obs| obs.irritation == YesNo::Yes) {
            caveats.push("Early termination due to persistent irritation.".to_string());
        } else {
            caveats.push("Early termination.".to_string());
        }
    }
    if late_backfill_excluded > 0 {
        caveats.push(format!(
            "{late_backfill_excluded} late-backfill day(s) excluded from analysis."
        ));
    }
    if let Some(warning) = imbalance_warning {
        caveats.push(warning);
    }
    if let Some(warning) = underpowered_warning {
        caveats.push(warning);
    }
    if planned_days_defaulted {
        caveats.push("planned_days missing from protocol; defaulted to 42.".to_string());
    }
    caveats.extend(data_warnings.iter().cloned());
    caveats.join(" ")
}

fn round2(value: f64) -> f64 {
    round_scale(value, 100.0)
}

fn round4(value: f64) -> f64 {
    round_scale(value, 10_000.0)
}

fn round_scale(value: f64, scale: f64) -> f64 {
    let scaled = value * scale;
    if scaled >= 0.0 {
        (scaled + 0.5).floor() / scale
    } else {
        (scaled - 0.5).ceil() / scale
    }
}

#[cfg(test)]
mod tests {
    use std::fs;
    use std::path::Path;

    use super::*;

    #[test]
    fn analysis_matches_high_quality_fixture() {
        let (protocol, observations, expected) = load_fixture("res-001");
        let result = analyze_result(protocol, observations).unwrap();

        assert_eq!(result.quality_grade, QualityGrade::A);
        assert_close(
            result.difference.unwrap(),
            expected["difference"].as_f64().unwrap(),
            0.15,
        );
        assert_close(
            result.ci_lower.unwrap(),
            expected["ci_lower"].as_f64().unwrap(),
            0.2,
        );
        assert_close(
            result.ci_upper.unwrap(),
            expected["ci_upper"].as_f64().unwrap(),
            0.2,
        );
    }

    #[test]
    fn analysis_excludes_late_backfills() {
        let (protocol, observations, expected) = load_fixture("res-007");
        let result = analyze_result(protocol, observations).unwrap();

        assert_eq!(result.late_backfill_excluded, 6);
        assert_close(
            result.difference.unwrap(),
            expected["difference"].as_f64().unwrap(),
            0.15,
        );
    }

    fn load_fixture(case_id: &str) -> (Value, Vec<Observation>, Value) {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
        let protocol = fs::read_to_string(
            root.join("benchmarks")
                .join("analysis_fixtures")
                .join(format!("{case_id}_protocol.json")),
        )
        .unwrap();
        let observations = fs::read_to_string(
            root.join("benchmarks")
                .join("analysis_fixtures")
                .join(format!("{case_id}_observations.csv")),
        )
        .unwrap();
        let expected = fs::read_to_string(
            root.join("benchmarks")
                .join("expected_outputs")
                .join(format!("{case_id}.json")),
        )
        .unwrap();

        (
            serde_json::from_str(&protocol).unwrap(),
            parse_observations_csv(&observations),
            serde_json::from_str(&expected).unwrap(),
        )
    }

    fn parse_observations_csv(content: &str) -> Vec<Observation> {
        let mut lines = content.lines();
        let headers: Vec<&str> = lines.next().unwrap().split(',').collect();
        lines
            .filter(|line| !line.trim().is_empty())
            .map(|line| {
                let values: Vec<&str> = line.split(',').collect();
                let get = |name: &str| -> &str {
                    let idx = headers.iter().position(|header| *header == name).unwrap();
                    values.get(idx).copied().unwrap_or("")
                };
                Observation {
                    day_index: get("day_index").parse().unwrap(),
                    date: get("date").to_string(),
                    condition: match get("condition") {
                        "A" => Condition::A,
                        "B" => Condition::B,
                        other => panic!("unexpected condition {other}"),
                    },
                    primary_score: get("primary_score").parse().ok(),
                    irritation: if get("irritation") == "yes" {
                        YesNo::Yes
                    } else {
                        YesNo::No
                    },
                    adherence: match get("adherence") {
                        "partial" => Adherence::Partial,
                        "no" => Adherence::No,
                        _ => Adherence::Yes,
                    },
                    note: get("note").to_string(),
                    is_backfill: if get("is_backfill") == "yes" {
                        YesNo::Yes
                    } else {
                        YesNo::No
                    },
                    backfill_days: get("backfill_days").parse().ok(),
                }
            })
            .collect()
    }

    fn assert_close(actual: f64, expected: f64, tolerance: f64) {
        assert!(
            (actual - expected).abs() < tolerance,
            "expected {actual} within {tolerance} of {expected}"
        );
    }
}

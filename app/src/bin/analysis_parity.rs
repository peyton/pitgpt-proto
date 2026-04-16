use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;

use pitgpt_tauri::{
    analyze_result, Adherence, AdverseEventSeverity, Condition, Observation, YesNo,
};
use serde_json::Value;

fn main() -> Result<(), String> {
    let args = std::env::args().collect::<Vec<_>>();
    if args.len() != 3 {
        return Err("usage: analysis_parity <protocol.json> <observations.csv>".to_string());
    }

    let protocol_path = PathBuf::from(&args[1]);
    let observations_path = PathBuf::from(&args[2]);
    let protocol: Value = serde_json::from_str(
        &fs::read_to_string(&protocol_path)
            .map_err(|err| format!("failed to read protocol: {err}"))?,
    )
    .map_err(|err| format!("failed to parse protocol JSON: {err}"))?;
    let observations = parse_observations_csv(
        &fs::read_to_string(&observations_path)
            .map_err(|err| format!("failed to read observations: {err}"))?,
    )?;

    let result = analyze_result(protocol, observations)?;
    println!(
        "{}",
        serde_json::to_string(&result).map_err(|err| format!("failed to encode result: {err}"))?
    );
    Ok(())
}

fn parse_observations_csv(content: &str) -> Result<Vec<Observation>, String> {
    let mut lines = content.lines();
    let headers = split_csv_line(
        lines
            .next()
            .ok_or_else(|| "observations CSV missing header".to_string())?,
    )
    .into_iter()
    .map(|item| item.trim().to_string())
    .collect::<Vec<_>>();

    lines
        .filter(|line| !line.trim().is_empty())
        .map(|line| {
            let values = split_csv_line(line);
            let get = |name: &str| -> &str {
                headers
                    .iter()
                    .position(|header| header == name)
                    .and_then(|index| values.get(index).map(String::as_str))
                    .unwrap_or("")
                    .trim()
            };

            Ok(Observation {
                observation_id: get("observation_id").to_string(),
                day_index: get("day_index")
                    .parse()
                    .map_err(|err| format!("invalid day_index: {err}"))?,
                date: get("date").to_string(),
                condition: parse_condition(get("condition"))?,
                assigned_condition: parse_optional_condition(get("assigned_condition"))?,
                actual_condition: parse_optional_condition(get("actual_condition"))?,
                primary_score: parse_optional_f64(get("primary_score")),
                irritation: parse_yes_no(get("irritation")),
                adherence: parse_adherence(get("adherence")),
                adherence_reason: get("adherence_reason").to_string(),
                note: get("note").to_string(),
                is_backfill: parse_yes_no(get("is_backfill")),
                backfill_days: parse_optional_f64(get("backfill_days")),
                adverse_event_severity: parse_adverse_event_severity(get(
                    "adverse_event_severity",
                ))?,
                adverse_event_description: get("adverse_event_description").to_string(),
                secondary_scores: parse_json_map_f64(get("secondary_scores"))?,
                recorded_at: get("recorded_at").to_string(),
                timezone: get("timezone").to_string(),
                planned_checkin_time: get("planned_checkin_time").to_string(),
                minutes_from_planned_checkin: get("minutes_from_planned_checkin").parse().ok(),
                exposure_start_at: get("exposure_start_at").to_string(),
                exposure_end_at: get("exposure_end_at").to_string(),
                measurement_timing: get("measurement_timing").to_string(),
                deviation_codes: parse_json_vec_string(get("deviation_codes"))?,
                confounders: parse_json_map_string(get("confounders"))?,
                rescue_action: get("rescue_action").to_string(),
            })
        })
        .collect()
}

fn split_csv_line(line: &str) -> Vec<String> {
    let mut fields = Vec::new();
    let mut current = String::new();
    let mut chars = line.chars().peekable();
    let mut in_quotes = false;
    while let Some(ch) = chars.next() {
        if ch == '"' {
            if in_quotes && chars.peek() == Some(&'"') {
                current.push('"');
                chars.next();
            } else {
                in_quotes = !in_quotes;
            }
        } else if ch == ',' && !in_quotes {
            fields.push(current);
            current = String::new();
        } else {
            current.push(ch);
        }
    }
    fields.push(current);
    fields
}

fn parse_condition(value: &str) -> Result<Condition, String> {
    match value {
        "A" => Ok(Condition::A),
        "B" => Ok(Condition::B),
        other => Err(format!("invalid condition: {other}")),
    }
}

fn parse_optional_condition(value: &str) -> Result<Option<Condition>, String> {
    if value.is_empty() {
        Ok(None)
    } else {
        parse_condition(value).map(Some)
    }
}

fn parse_yes_no(value: &str) -> YesNo {
    if value == "yes" {
        YesNo::Yes
    } else {
        YesNo::No
    }
}

fn parse_adherence(value: &str) -> Adherence {
    match value {
        "partial" => Adherence::Partial,
        "no" => Adherence::No,
        _ => Adherence::Yes,
    }
}

fn parse_adverse_event_severity(value: &str) -> Result<Option<AdverseEventSeverity>, String> {
    match value {
        "" => Ok(None),
        "mild" => Ok(Some(AdverseEventSeverity::Mild)),
        "moderate" => Ok(Some(AdverseEventSeverity::Moderate)),
        "severe" => Ok(Some(AdverseEventSeverity::Severe)),
        other => Err(format!("invalid adverse_event_severity: {other}")),
    }
}

fn parse_optional_f64(value: &str) -> Option<f64> {
    if value.is_empty() {
        None
    } else {
        value.parse().ok()
    }
}

fn parse_json_map_f64(value: &str) -> Result<BTreeMap<String, f64>, String> {
    if value.is_empty() {
        return Ok(BTreeMap::new());
    }
    serde_json::from_str(value).map_err(|err| format!("invalid secondary_scores: {err}"))
}

fn parse_json_map_string(value: &str) -> Result<BTreeMap<String, String>, String> {
    if value.is_empty() {
        return Ok(BTreeMap::new());
    }
    serde_json::from_str(value).map_err(|err| format!("invalid confounders: {err}"))
}

fn parse_json_vec_string(value: &str) -> Result<Vec<String>, String> {
    if value.is_empty() {
        return Ok(vec![]);
    }
    serde_json::from_str(value).map_err(|err| format!("invalid deviation_codes: {err}"))
}

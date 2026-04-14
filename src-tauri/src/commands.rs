use std::collections::HashMap;
use std::future::Future;
use std::sync::Mutex;

use serde_json::Value;
use tauri::{AppHandle, State};
use tokio::sync::oneshot;

use crate::analysis::analyze_result;
use crate::ingestion::ingest_local_result;
use crate::models::{
    Assignment, Observation, ProviderInfo, ProviderKind, ResultCard, TrialTemplate,
};
use crate::providers::discover_provider_infos;
use crate::schedule::generate_schedule_result;
use crate::storage::{
    app_data_dir, clear_state_in_dir, export_to_dir, load_state_from_dir, save_state_to_dir,
};
use crate::templates::load_templates as load_templates_shared;

const INGEST_CANCELLED_MESSAGE: &str = "Ingestion cancelled.";

#[derive(Default)]
pub struct IngestCancellationState {
    pending: Mutex<HashMap<String, oneshot::Sender<()>>>,
}

impl IngestCancellationState {
    fn register(&self, request_id: &str) -> Result<oneshot::Receiver<()>, String> {
        let mut pending = self
            .pending
            .lock()
            .map_err(|_| "ingestion cancellation state is unavailable".to_string())?;
        if pending.contains_key(request_id) {
            return Err("Ingestion request is already running.".to_string());
        }
        let (sender, receiver) = oneshot::channel();
        pending.insert(request_id.to_string(), sender);
        Ok(receiver)
    }

    fn cancel(&self, request_id: &str) -> Result<bool, String> {
        let sender = self
            .pending
            .lock()
            .map_err(|_| "ingestion cancellation state is unavailable".to_string())?
            .remove(request_id);
        Ok(sender.is_some_and(|sender| sender.send(()).is_ok()))
    }

    fn clear(&self, request_id: &str) -> Result<(), String> {
        self.pending
            .lock()
            .map_err(|_| "ingestion cancellation state is unavailable".to_string())?
            .remove(request_id);
        Ok(())
    }
}

#[tauri::command]
pub fn get_templates() -> Result<Vec<TrialTemplate>, String> {
    load_templates_shared()
}

#[tauri::command]
pub fn generate_schedule(
    duration_weeks: u32,
    block_length_days: u32,
    seed: u32,
) -> Result<Vec<Assignment>, String> {
    generate_schedule_result(duration_weeks, block_length_days, seed)
}

#[tauri::command]
pub fn analyze(protocol: Value, observations: Vec<Observation>) -> Result<ResultCard, String> {
    analyze_result(protocol, observations)
}

#[tauri::command]
pub fn analyze_example() -> Result<ResultCard, String> {
    let protocol: Value = serde_json::from_str(include_str!("../../examples/protocol.json"))
        .map_err(|err| format!("invalid bundled example protocol: {err}"))?;
    let observations = parse_example_observations(include_str!("../../examples/observations.csv"))?;
    analyze_result(protocol, observations)
}

#[tauri::command]
pub fn load_app_state(app: AppHandle) -> Result<Option<Value>, String> {
    load_state_from_dir(&app_data_dir(&app)?)
}

#[tauri::command]
pub fn save_app_state(app: AppHandle, state: Value) -> Result<(), String> {
    save_state_to_dir(&app_data_dir(&app)?, &state)
}

#[tauri::command]
pub fn clear_app_state(app: AppHandle) -> Result<(), String> {
    clear_state_in_dir(&app_data_dir(&app)?)
}

#[tauri::command]
pub fn export_file(app: AppHandle, filename: String, content: String) -> Result<String, String> {
    let path = export_to_dir(&app_data_dir(&app)?, &filename, &content)?;
    Ok(path.to_string_lossy().to_string())
}

#[tauri::command]
pub async fn discover_ai_tools() -> Result<Vec<ProviderInfo>, String> {
    Ok(discover_provider_infos().await)
}

#[tauri::command]
pub async fn ingest_local(
    query: String,
    documents: Vec<String>,
    provider: ProviderKind,
    model: Option<String>,
    request_id: Option<String>,
    cancellation: State<'_, IngestCancellationState>,
) -> Result<Value, String> {
    run_ingest_with_optional_cancellation(request_id, &cancellation, async move {
        ingest_local_result(query, documents, provider, model).await
    })
    .await
}

#[tauri::command]
pub fn cancel_ingest_local(
    request_id: String,
    cancellation: State<'_, IngestCancellationState>,
) -> Result<bool, String> {
    cancellation.cancel(&request_id)
}

async fn run_ingest_with_optional_cancellation<F>(
    request_id: Option<String>,
    cancellation: &IngestCancellationState,
    ingest: F,
) -> Result<Value, String>
where
    F: Future<Output = Result<Value, String>>,
{
    let Some(request_id) = request_id else {
        return ingest.await;
    };
    let cancel = cancellation.register(&request_id)?;
    let result = tokio::select! {
        result = ingest => result,
        _ = cancel => Err(INGEST_CANCELLED_MESSAGE.to_string()),
    };
    cancellation.clear(&request_id)?;
    result
}

fn parse_example_observations(content: &str) -> Result<Vec<Observation>, String> {
    let mut lines = content.lines();
    let headers: Vec<&str> = lines
        .next()
        .ok_or_else(|| "example observations missing header".to_string())?
        .split(',')
        .collect();

    lines
        .filter(|line| !line.trim().is_empty())
        .map(|line| {
            let values: Vec<&str> = line.split(',').collect();
            let get = |name: &str| -> &str {
                headers
                    .iter()
                    .position(|header| *header == name)
                    .and_then(|idx| values.get(idx).copied())
                    .unwrap_or("")
            };
            Ok(Observation {
                day_index: get("day_index")
                    .parse()
                    .map_err(|err| format!("invalid day_index: {err}"))?,
                date: get("date").to_string(),
                condition: serde_json::from_str(&format!("\"{}\"", get("condition")))
                    .map_err(|err| format!("invalid condition: {err}"))?,
                primary_score: get("primary_score").parse().ok(),
                irritation: serde_json::from_str(&format!("\"{}\"", get("irritation")))
                    .unwrap_or(crate::models::YesNo::No),
                adherence: serde_json::from_str(&format!("\"{}\"", get("adherence")))
                    .unwrap_or(crate::models::Adherence::Yes),
                note: get("note").to_string(),
                is_backfill: serde_json::from_str(&format!("\"{}\"", get("is_backfill")))
                    .unwrap_or(crate::models::YesNo::No),
                backfill_days: get("backfill_days").parse().ok(),
            })
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;
    use std::time::Duration;

    use serde_json::json;

    use super::*;

    #[tokio::test]
    async fn cancels_registered_ingestion_request() {
        let cancellation = Arc::new(IngestCancellationState::default());
        let task_cancellation = Arc::clone(&cancellation);
        let request_id = "req-cancel-native".to_string();
        let task_request_id = request_id.clone();
        let handle = tokio::spawn(async move {
            run_ingest_with_optional_cancellation(
                Some(task_request_id),
                &task_cancellation,
                async {
                    tokio::time::sleep(Duration::from_secs(60)).await;
                    Ok(json!({"decision": "block"}))
                },
            )
            .await
        });

        let mut cancelled = false;
        for _ in 0..10 {
            if cancellation.cancel(&request_id).unwrap() {
                cancelled = true;
                break;
            }
            tokio::time::sleep(Duration::from_millis(10)).await;
        }

        assert!(cancelled);
        let err = handle.await.unwrap().unwrap_err();
        assert_eq!(err, INGEST_CANCELLED_MESSAGE);
        assert!(!cancellation
            .pending
            .lock()
            .unwrap()
            .contains_key(&request_id));
    }

    #[test]
    fn cancelling_unknown_ingestion_request_reports_false() {
        let cancellation = IngestCancellationState::default();

        assert!(!cancellation.cancel("missing").unwrap());
    }
}

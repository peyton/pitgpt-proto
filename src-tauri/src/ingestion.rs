use serde_json::Value;

use crate::models::ProviderKind;

const SAFETY_POLICY: &str = include_str!("../../shared/safety_policy.md");
const MAX_DOCUMENT_CHARS: usize = 12_000;
const MAX_TOTAL_DOCUMENT_CHARS: usize = 40_000;

pub async fn ingest_local_result(
    query: String,
    documents: Vec<String>,
    provider: ProviderKind,
    model: Option<String>,
) -> Result<Value, String> {
    match provider {
        ProviderKind::Ollama => {
            let model = model.unwrap_or_else(|| "llama3.1".to_string());
            ingest_ollama("http://localhost:11434", &model, &query, &documents).await
        }
        ProviderKind::IosOnDevice => Err(
            "iOS on-device models are reserved for future work and are not available yet."
                .to_string(),
        ),
        other => Err(format!(
            "Provider {other:?} is not available for local native ingestion yet."
        )),
    }
}

pub async fn ingest_ollama(
    base_url: &str,
    model: &str,
    query: &str,
    documents: &[String],
) -> Result<Value, String> {
    validate_inputs(query, documents)?;
    let user_message = build_user_message(query, documents);
    let payload = serde_json::json!({
        "model": model,
        "stream": false,
        "format": "json",
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": SAFETY_POLICY},
            {"role": "user", "content": user_message}
        ]
    });

    let url = format!("{}/api/chat", base_url.trim_end_matches('/'));
    let data: Value = reqwest::Client::new()
        .post(url)
        .json(&payload)
        .send()
        .await
        .map_err(|err| format!("Ollama request failed: {err}"))?
        .error_for_status()
        .map_err(|err| format!("Ollama request failed: {err}"))?
        .json()
        .await
        .map_err(|err| format!("Ollama response was not JSON: {err}"))?;

    let content = data
        .get("message")
        .and_then(|message| message.get("content"))
        .and_then(|content| content.as_str())
        .ok_or_else(|| "Ollama response missing message content".to_string())?;
    let mut result: Value = serde_json::from_str(content)
        .map_err(|err| format!("Ollama content was not JSON: {err}"))?;
    if let Some(obj) = result.as_object_mut() {
        obj.entry("model")
            .or_insert(Value::String(model.to_string()));
        obj.entry("response_validation_status")
            .or_insert(Value::String("validated".to_string()));
    }
    validate_ingestion_result(&result)?;
    Ok(result)
}

fn build_user_message(query: &str, documents: &[String]) -> String {
    let mut parts = vec![format!("User query: {}", query.trim())];
    for (idx, doc) in documents.iter().enumerate() {
        parts.push(format!("\n--- Uploaded Document {} ---\n{doc}", idx + 1));
    }
    parts.join("\n")
}

fn validate_inputs(query: &str, documents: &[String]) -> Result<(), String> {
    if query.trim().is_empty() {
        return Err("Query is required.".to_string());
    }
    let mut total = 0;
    for (idx, doc) in documents.iter().enumerate() {
        total += doc.len();
        if doc.len() > MAX_DOCUMENT_CHARS {
            return Err(format!(
                "Document {} is too large ({} chars). Limit each source to {MAX_DOCUMENT_CHARS} chars.",
                idx + 1,
                doc.len()
            ));
        }
    }
    if total > MAX_TOTAL_DOCUMENT_CHARS {
        return Err(format!(
            "Sources are too large in total ({total} chars). Limit all sources to {MAX_TOTAL_DOCUMENT_CHARS} chars."
        ));
    }
    Ok(())
}

fn validate_ingestion_result(value: &Value) -> Result<(), String> {
    let obj = value
        .as_object()
        .ok_or_else(|| "ingestion result must be a JSON object".to_string())?;
    for key in [
        "decision",
        "safety_tier",
        "evidence_quality",
        "user_message",
    ] {
        if !obj.contains_key(key) {
            return Err(format!("ingestion result missing {key}"));
        }
    }
    let decision = obj
        .get("decision")
        .and_then(|value| value.as_str())
        .unwrap_or_default();
    let protocol = obj.get("protocol");
    if matches!(
        decision,
        "generate_protocol" | "generate_protocol_with_restrictions"
    ) && !protocol.is_some_and(|value| value.is_object())
    {
        return Err("generated protocol decisions require protocol".to_string());
    }
    if matches!(decision, "block" | "manual_review_before_protocol")
        && protocol.is_some_and(|value| !value.is_null())
    {
        return Err("blocked or manual-review decisions must not include protocol".to_string());
    }
    let has_block_reason = obj
        .get("block_reason")
        .and_then(|value| value.as_str())
        .is_some_and(|value| !value.trim().is_empty());
    if decision == "block" && !has_block_reason {
        return Err("block decisions require block_reason".to_string());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn rejects_reserved_ios_provider() {
        let err = ingest_local_result("test".to_string(), vec![], ProviderKind::IosOnDevice, None)
            .await
            .unwrap_err();

        assert!(err.contains("reserved"));
    }

    #[test]
    fn validates_document_limits_before_provider_call() {
        let err = validate_inputs("test", &["x".repeat(12_001)]).unwrap_err();
        assert!(err.contains("too large"));
    }

    #[test]
    fn trims_query_in_provider_prompt() {
        let prompt = build_user_message("  compare routines  ", &[]);

        assert_eq!(prompt, "User query: compare routines");
    }

    #[test]
    fn validates_block_reason_contract() {
        let err = validate_ingestion_result(&serde_json::json!({
            "decision": "block",
            "safety_tier": "RED",
            "evidence_quality": "weak",
            "protocol": null,
            "user_message": "No.",
            "block_reason": "",
        }))
        .unwrap_err();

        assert!(err.contains("block_reason"));
    }
}

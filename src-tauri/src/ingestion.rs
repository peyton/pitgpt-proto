use serde_json::{Map, Value};
use std::time::Duration;

use crate::models::{Protocol, ProviderKind};

const SAFETY_POLICY: &str = include_str!("../../shared/safety_policy.md");
const SOURCE_FETCH_TIMEOUT_S: u64 = 20;
const PROTOCOL_FOLLOW_UP_STEPS: [&str; 3] = [
    "What are the exact two routines, products, or behaviors you want to compare?",
    "What single daily 0-10 outcome should decide which option worked better for you?",
    "Are any medications, symptoms, pregnancy, urgent issues, or clinician instructions involved?",
];

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
    let documents = resolve_documents(documents).await?;
    let total_document_chars: usize = documents.iter().map(String::len).sum();
    log::info!(
        target: "pitgpt::ingestion",
        "starting local ingestion provider=ollama model={model} documents={} total_document_chars={total_document_chars}",
        documents.len()
    );
    let user_message = build_user_message(query, &documents);
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
    let mut result: Value = match serde_json::from_str(content) {
        Ok(result) => result,
        Err(err) => {
            log::warn!(
                target: "pitgpt::ingestion",
                "local provider returned non-json content model={model}: {err}"
            );
            manual_review_result(
                model,
                "The local model did not return a complete protocol.",
                "provider_content_not_json",
            )
        }
    };
    normalize_ingestion_result(&mut result, model)?;
    validate_ingestion_result(&result)?;
    log::info!(
        target: "pitgpt::ingestion",
        "local ingestion completed model={model} decision={} status={}",
        result.get("decision").and_then(Value::as_str).unwrap_or("unknown"),
        result
            .get("response_validation_status")
            .and_then(Value::as_str)
            .unwrap_or("unknown")
    );
    Ok(result)
}

fn build_user_message(query: &str, documents: &[String]) -> String {
    let mut parts = vec![format!("User query: {}", query.trim())];
    for (idx, doc) in documents.iter().enumerate() {
        parts.push(format!("\n--- Uploaded Document {} ---\n{doc}", idx + 1));
    }
    parts.join("\n")
}

fn validate_inputs(query: &str, _documents: &[String]) -> Result<(), String> {
    if query.trim().is_empty() {
        return Err("Query is required.".to_string());
    }
    Ok(())
}

async fn resolve_documents(documents: &[String]) -> Result<Vec<String>, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(SOURCE_FETCH_TIMEOUT_S))
        .build()
        .map_err(|err| format!("failed to create source fetch client: {err}"))?;
    let mut resolved = Vec::with_capacity(documents.len());
    for doc in documents {
        let source = doc.trim();
        if !is_url_source(source) {
            resolved.push(doc.clone());
            continue;
        }
        log::info!(
            target: "pitgpt::ingestion",
            "fetching source url for local ingestion"
        );
        resolved.push(fetch_url_source(&client, source).await?);
    }
    Ok(resolved)
}

fn is_url_source(source: &str) -> bool {
    (source.starts_with("https://") || source.starts_with("http://"))
        && !source.chars().any(char::is_whitespace)
}

async fn fetch_url_source(client: &reqwest::Client, url: &str) -> Result<String, String> {
    let response = client
        .get(url)
        .send()
        .await
        .map_err(|err| format!("Could not fetch source URL {url}: {err}"))?
        .error_for_status()
        .map_err(|err| format!("Could not fetch source URL {url}: {err}"))?;
    let content_type = response
        .headers()
        .get(reqwest::header::CONTENT_TYPE)
        .and_then(|value| value.to_str().ok())
        .unwrap_or("")
        .to_ascii_lowercase();
    let body = response
        .text()
        .await
        .map_err(|err| format!("Could not read source URL {url}: {err}"))?;
    let text = if content_type.contains("text/html") {
        html_to_text(&body)
    } else if content_type.starts_with("text/")
        || content_type.contains("json")
        || content_type.contains("xml")
    {
        body
    } else {
        format!(
            "Content type: {}\nThe linked resource was not directly text-readable. Upload a text PDF or paste the article text if the source content is needed.",
            if content_type.is_empty() {
                "unknown"
            } else {
                &content_type
            }
        )
    };
    Ok(format!("Source URL: {url}\n\n{}", text.trim()))
}

fn html_to_text(html: &str) -> String {
    let mut text = String::with_capacity(html.len());
    let mut in_tag = false;
    let mut tag = String::new();
    let mut skip_depth = 0_u32;
    for ch in html.chars() {
        match ch {
            '<' => {
                in_tag = true;
                tag.clear();
                text.push(' ');
            }
            '>' => {
                in_tag = false;
                update_skip_depth(&tag, &mut skip_depth);
                text.push(' ');
            }
            _ if in_tag => tag.push(ch),
            _ if skip_depth == 0 => text.push(ch),
            _ => {}
        }
    }
    text.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn update_skip_depth(tag: &str, skip_depth: &mut u32) {
    let normalized = tag.trim().to_ascii_lowercase();
    if normalized.starts_with("script")
        || normalized.starts_with("style")
        || normalized.starts_with("noscript")
    {
        *skip_depth += 1;
    } else if (normalized.starts_with("/script")
        || normalized.starts_with("/style")
        || normalized.starts_with("/noscript"))
        && *skip_depth > 0
    {
        *skip_depth -= 1;
    }
}

fn normalize_ingestion_result(value: &mut Value, model: &str) -> Result<(), String> {
    let obj = value
        .as_object_mut()
        .ok_or_else(|| "ingestion result must be a JSON object".to_string())?;
    obj.entry("model")
        .or_insert(Value::String(model.to_string()));
    obj.entry("response_validation_status")
        .or_insert(Value::String("validated".to_string()));
    obj.entry("evidence_conflict").or_insert(Value::Bool(false));

    let decision = obj
        .get("decision")
        .and_then(Value::as_str)
        .unwrap_or_default();
    if !matches!(
        decision,
        "generate_protocol" | "generate_protocol_with_restrictions"
    ) {
        return Ok(());
    }

    let protocol_issue =
        match obj.get("protocol") {
            Some(protocol) if protocol.is_object() => serde_json::from_value::<Protocol>(
                protocol.clone(),
            )
            .err()
            .map(|err| {
                format!("The model returned a protocol, but it was missing required details: {err}")
            }),
            _ => Some("The model did not return a complete protocol.".to_string()),
        };

    if let Some(issue) = protocol_issue {
        let status = if obj.get("protocol").is_some_and(Value::is_object) {
            "provider_protocol_invalid"
        } else {
            "provider_protocol_missing"
        };
        log::warn!(
            target: "pitgpt::ingestion",
            "downgrading incomplete provider protocol to manual review model={model} status={status}: {issue}"
        );
        downgrade_to_manual_review(obj, &issue, status);
    }
    Ok(())
}

fn manual_review_result(model: &str, reason: &str, status: &str) -> Value {
    serde_json::json!({
        "decision": "manual_review_before_protocol",
        "safety_tier": "YELLOW",
        "evidence_quality": "novel",
        "evidence_conflict": false,
        "risk_level": "low",
        "risk_rationale": "",
        "clinician_note": "",
        "protocol": null,
        "block_reason": reason,
        "user_message": "I need a little more detail before I can lock this protocol. Answer the follow-up questions and try again.",
        "model": model,
        "response_validation_status": status,
        "source_summaries": [],
        "claimed_outcomes": [],
        "sources": [],
        "extracted_claims": [],
        "suitability_scores": [],
        "next_steps": PROTOCOL_FOLLOW_UP_STEPS,
    })
}

fn downgrade_to_manual_review(obj: &mut Map<String, Value>, reason: &str, status: &str) {
    obj.insert(
        "decision".to_string(),
        Value::String("manual_review_before_protocol".to_string()),
    );
    obj.entry("safety_tier".to_string())
        .or_insert(Value::String("YELLOW".to_string()));
    obj.entry("evidence_quality".to_string())
        .or_insert(Value::String("novel".to_string()));
    obj.entry("risk_level".to_string())
        .or_insert(Value::String("low".to_string()));
    obj.entry("risk_rationale".to_string())
        .or_insert(Value::String(String::new()));
    obj.entry("clinician_note".to_string())
        .or_insert(Value::String(String::new()));
    obj.insert("protocol".to_string(), Value::Null);
    obj.insert(
        "block_reason".to_string(),
        Value::String(reason.to_string()),
    );
    obj.insert(
        "user_message".to_string(),
        Value::String(
            "I need a little more detail before I can lock this protocol. Answer the follow-up questions and try again."
                .to_string(),
        ),
    );
    obj.insert(
        "response_validation_status".to_string(),
        Value::String(status.to_string()),
    );
    if !obj
        .get("next_steps")
        .and_then(Value::as_array)
        .is_some_and(|steps| !steps.is_empty())
    {
        obj.insert("next_steps".to_string(), follow_up_steps_value());
    }
}

fn follow_up_steps_value() -> Value {
    Value::Array(
        PROTOCOL_FOLLOW_UP_STEPS
            .iter()
            .map(|step| Value::String((*step).to_string()))
            .collect(),
    )
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
    fn allows_large_documents_before_provider_call() {
        validate_inputs("test", &["x".repeat(120_001)]).unwrap();
    }

    #[test]
    fn strips_html_for_url_sources() {
        let text = html_to_text(
            "<html><body><h1>Title</h1><script>bad()</script><p>Useful text.</p></body></html>",
        );

        assert!(text.contains("Title"));
        assert!(text.contains("Useful text."));
        assert!(!text.contains("bad()"));
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

    #[test]
    fn generated_decision_without_protocol_asks_follow_up() {
        let mut result = serde_json::json!({
            "decision": "generate_protocol",
            "safety_tier": "GREEN",
            "evidence_quality": "novel",
            "protocol": null,
            "user_message": "Ready.",
        });

        normalize_ingestion_result(&mut result, "test-model").unwrap();
        validate_ingestion_result(&result).unwrap();

        assert_eq!(result["decision"], "manual_review_before_protocol");
        assert!(result["protocol"].is_null());
        assert_eq!(
            result["response_validation_status"],
            "provider_protocol_missing"
        );
        assert!(result["next_steps"].as_array().unwrap().len() >= 3);
    }

    #[test]
    fn generated_decision_with_invalid_protocol_asks_follow_up() {
        let mut result = serde_json::json!({
            "decision": "generate_protocol",
            "safety_tier": "GREEN",
            "evidence_quality": "novel",
            "protocol": {
                "cadence": "daily",
                "washout": "None",
                "primary_outcome_question": "Comfort (0-10)"
            },
            "user_message": "Ready.",
        });

        normalize_ingestion_result(&mut result, "test-model").unwrap();
        validate_ingestion_result(&result).unwrap();

        assert_eq!(result["decision"], "manual_review_before_protocol");
        assert!(result["protocol"].is_null());
        assert_eq!(
            result["response_validation_status"],
            "provider_protocol_invalid"
        );
        assert!(result["block_reason"]
            .as_str()
            .unwrap()
            .contains("missing required details"));
    }
}

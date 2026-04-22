use crate::models::{ProviderKind, WorkflowDefinition};
use crate::providers::fetch_ollama_models;

const WORKFLOWS_JSON: &str = include_str!("../../shared/workflows.json");

pub fn load_workflows() -> Result<Vec<WorkflowDefinition>, String> {
    serde_json::from_str(WORKFLOWS_JSON).map_err(|err| format!("invalid shared workflows: {err}"))
}

pub fn get_workflow(workflow_id: &str) -> Result<Option<WorkflowDefinition>, String> {
    let workflows = load_workflows()?;
    Ok(workflows
        .into_iter()
        .find(|workflow| workflow.id == workflow_id))
}

pub fn build_workflow_query(query: &str, workflow: Option<&WorkflowDefinition>) -> String {
    let trimmed_query = query.trim();
    match workflow {
        None => trimmed_query.to_string(),
        Some(workflow) => format!(
            "Workflow mode: {}\nWorkflow objective: {}\nWorkflow constraints:\n{}\nWhen uncertain, prefer manual_review_before_protocol over overconfident protocol generation.\nUser request:\n{}",
            workflow.title, workflow.objective, workflow.prompt_scaffold, trimmed_query
        ),
    }
}

pub async fn resolve_workflow_model(
    workflow: Option<&WorkflowDefinition>,
    provider: ProviderKind,
    requested_model: Option<String>,
    fallback_model: &str,
    ollama_base_url: &str,
) -> (String, Option<String>) {
    if let Some(model) = requested_model {
        return (model, None);
    }
    let Some(workflow) = workflow else {
        return (fallback_model.to_string(), None);
    };
    let Some(candidate) = workflow_model_candidate(workflow, provider) else {
        return (
            fallback_model.to_string(),
            Some(format!(
                "Workflow {} did not provide a MedGemma default for {}. Using fallback model {}.",
                workflow.id,
                provider_label(provider),
                fallback_model
            )),
        );
    };
    if provider == ProviderKind::Ollama {
        match fetch_ollama_models(ollama_base_url).await {
            Ok(models) if models.contains(&candidate) => {}
            Ok(_) => {
                return (
                    fallback_model.to_string(),
                    Some(format!(
                        "Workflow {} requested {}, but that Ollama model was not found. Using fallback model {}.",
                        workflow.id, candidate, fallback_model
                    )),
                );
            }
            Err(_) => {
                return (
                    fallback_model.to_string(),
                    Some(format!(
                        "Could not verify Ollama model {} for workflow {}. Using fallback model {}.",
                        candidate, workflow.id, fallback_model
                    )),
                );
            }
        }
    }
    (candidate, None)
}

fn workflow_model_candidate(
    workflow: &WorkflowDefinition,
    provider: ProviderKind,
) -> Option<String> {
    if let Ok(value) = std::env::var(workflow_env_key(&workflow.id, provider)) {
        let trimmed = value.trim();
        if !trimmed.is_empty() {
            return Some(trimmed.to_string());
        }
    }
    if let Ok(value) = std::env::var(provider_override_env_key(provider)) {
        let trimmed = value.trim();
        if !trimmed.is_empty() {
            return Some(trimmed.to_string());
        }
    }
    workflow
        .recommended_models
        .get(provider_key(provider))
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
}

fn provider_override_env_key(provider: ProviderKind) -> &'static str {
    match provider {
        ProviderKind::Openrouter => "PITGPT_WORKFLOW_MEDGEMMA_MODEL_OPENROUTER",
        ProviderKind::Ollama => "PITGPT_WORKFLOW_MEDGEMMA_MODEL_OLLAMA",
        _ => "PITGPT_WORKFLOW_MEDGEMMA_MODEL",
    }
}

fn provider_key(provider: ProviderKind) -> &'static str {
    match provider {
        ProviderKind::Openrouter => "openrouter",
        ProviderKind::Ollama => "ollama",
        ProviderKind::ClaudeCli => "claude_cli",
        ProviderKind::CodexCli => "codex_cli",
        ProviderKind::ChatgptCli => "chatgpt_cli",
        ProviderKind::IosOnDevice => "ios_on_device",
    }
}

fn provider_label(provider: ProviderKind) -> &'static str {
    provider_key(provider)
}

fn workflow_env_key(workflow_id: &str, provider: ProviderKind) -> String {
    let mut normalized = String::new();
    let mut last_was_separator = false;
    for ch in workflow_id.chars() {
        if ch.is_ascii_alphanumeric() {
            normalized.push(ch.to_ascii_uppercase());
            last_was_separator = false;
        } else if !last_was_separator {
            normalized.push('_');
            last_was_separator = true;
        }
    }
    let normalized = normalized.trim_matches('_').to_string();
    format!(
        "PITGPT_WORKFLOW_MODEL_{}_{}",
        normalized,
        provider_key(provider).to_ascii_uppercase()
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn loads_shared_workflows() {
        let workflows = load_workflows().unwrap();
        assert!(workflows
            .iter()
            .any(|workflow| workflow.id == "genotype_routine_hypothesis"));
        assert!(workflows
            .iter()
            .any(|workflow| workflow.id == "multiomics_crossover_designer"));
        assert!(workflows
            .iter()
            .any(|workflow| workflow.id == "adverse_signal_clinician_escalation"));
    }

    #[test]
    fn workflow_query_wraps_user_prompt() {
        let workflow = load_workflows()
            .unwrap()
            .into_iter()
            .find(|item| item.id == "genotype_routine_hypothesis")
            .unwrap();
        let query = build_workflow_query("Test query", Some(&workflow));
        assert!(query.contains("Workflow mode"));
        assert!(query.contains("Test query"));
    }
}

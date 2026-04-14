use crate::models::{ProviderInfo, ProviderKind, ProviderStatus};

pub async fn discover_provider_infos() -> Vec<ProviderInfo> {
    let mut providers = discover_platform_providers().await;
    providers.push(ProviderInfo {
        kind: ProviderKind::Openrouter,
        label: "OpenRouter".to_string(),
        status: ProviderStatus::InstalledUnavailable,
        is_local: false,
        is_offline: false,
        models: vec![],
        detail: "Cloud provider remains available through the web/API target.".to_string(),
    });
    providers.push(ProviderInfo {
        kind: ProviderKind::IosOnDevice,
        label: "iOS On-Device Models".to_string(),
        status: ProviderStatus::Reserved,
        is_local: true,
        is_offline: true,
        models: vec![],
        detail: "Reserved for future on-device model runtime work.".to_string(),
    });
    providers
}

#[cfg(target_os = "ios")]
async fn discover_platform_providers() -> Vec<ProviderInfo> {
    vec![]
}

#[cfg(not(target_os = "ios"))]
async fn discover_platform_providers() -> Vec<ProviderInfo> {
    vec![
        discover_ollama().await,
        cli_provider(ProviderKind::ClaudeCli, "Claude CLI", "claude"),
        cli_provider(ProviderKind::CodexCli, "Codex CLI", "codex"),
        cli_provider(ProviderKind::ChatgptCli, "ChatGPT CLI", "chatgpt"),
    ]
}

#[cfg(not(target_os = "ios"))]
async fn discover_ollama() -> ProviderInfo {
    if which::which("ollama").is_err() {
        return ProviderInfo {
            kind: ProviderKind::Ollama,
            label: "Ollama".to_string(),
            status: ProviderStatus::NotFound,
            is_local: true,
            is_offline: true,
            models: vec![],
            detail: "Ollama is not on PATH.".to_string(),
        };
    }

    match fetch_ollama_models("http://localhost:11434").await {
        Ok(models) if !models.is_empty() => ProviderInfo {
            kind: ProviderKind::Ollama,
            label: "Ollama".to_string(),
            status: ProviderStatus::Available,
            is_local: true,
            is_offline: true,
            models,
            detail: "Ollama is running.".to_string(),
        },
        Ok(_) => ProviderInfo {
            kind: ProviderKind::Ollama,
            label: "Ollama".to_string(),
            status: ProviderStatus::InstalledUnavailable,
            is_local: true,
            is_offline: true,
            models: vec![],
            detail: "Ollama is running but no models were found.".to_string(),
        },
        Err(err) => ProviderInfo {
            kind: ProviderKind::Ollama,
            label: "Ollama".to_string(),
            status: ProviderStatus::InstalledUnavailable,
            is_local: true,
            is_offline: true,
            models: vec![],
            detail: format!("Ollama is installed but not reachable: {err}"),
        },
    }
}

#[cfg(not(target_os = "ios"))]
pub async fn fetch_ollama_models(base_url: &str) -> Result<Vec<String>, String> {
    let url = format!("{}/api/tags", base_url.trim_end_matches('/'));
    let data: serde_json::Value = reqwest::Client::new()
        .get(url)
        .send()
        .await
        .map_err(|err| err.to_string())?
        .error_for_status()
        .map_err(|err| err.to_string())?
        .json()
        .await
        .map_err(|err| err.to_string())?;
    Ok(parse_ollama_models(&data))
}

pub fn parse_ollama_models(data: &serde_json::Value) -> Vec<String> {
    let mut models: Vec<String> = data
        .get("models")
        .and_then(|models| models.as_array())
        .map(|models| {
            models
                .iter()
                .filter_map(|item| item.get("name").and_then(|name| name.as_str()))
                .filter(|name| !name.trim().is_empty())
                .map(ToString::to_string)
                .collect()
        })
        .unwrap_or_default();
    models.sort();
    models.dedup();
    models
}

#[cfg(not(target_os = "ios"))]
fn cli_provider(kind: ProviderKind, label: &str, binary: &str) -> ProviderInfo {
    match which::which(binary) {
        Ok(path) => ProviderInfo {
            kind,
            label: label.to_string(),
            status: ProviderStatus::Available,
            is_local: true,
            is_offline: false,
            models: vec![],
            detail: format!("Found at {}.", path.display()),
        },
        Err(_) => ProviderInfo {
            kind,
            label: label.to_string(),
            status: ProviderStatus::NotFound,
            is_local: true,
            is_offline: false,
            models: vec![],
            detail: format!("{binary} is not on PATH."),
        },
    }
}

#[cfg(any(target_os = "ios", test))]
fn unsupported(kind: ProviderKind, label: &str) -> ProviderInfo {
    ProviderInfo {
        kind,
        label: label.to_string(),
        status: ProviderStatus::UnsupportedPlatform,
        is_local: true,
        is_offline: false,
        models: vec![],
        detail: "This provider is not available on iOS in this phase.".to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_ollama_model_names() {
        let data = serde_json::json!({
            "models": [
                {"name": "llama3.1:latest"},
                {"name": "mistral:latest"},
                {"name": "llama3.1:latest"},
                {"name": ""}
            ]
        });

        assert_eq!(
            parse_ollama_models(&data),
            vec!["llama3.1:latest".to_string(), "mistral:latest".to_string()]
        );
    }

    #[test]
    fn reserved_ios_provider_is_stable() {
        let provider = unsupported(ProviderKind::Ollama, "Ollama");

        assert_eq!(provider.status, ProviderStatus::UnsupportedPlatform);
    }
}

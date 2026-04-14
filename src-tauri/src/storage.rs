use std::fs;
use std::path::{Path, PathBuf};

use serde_json::Value;
use tauri::{AppHandle, Manager};

const STATE_FILE: &str = "pitgpt_state.json";
const EXPORT_DIR: &str = "exports";

pub fn load_state_from_dir(dir: &Path) -> Result<Option<Value>, String> {
    let path = dir.join(STATE_FILE);
    if !path.exists() {
        return Ok(None);
    }
    let raw = fs::read_to_string(&path)
        .map_err(|err| format!("failed to read state file {}: {err}", path.display()))?;
    serde_json::from_str(&raw)
        .map(Some)
        .map_err(|err| format!("failed to parse state file {}: {err}", path.display()))
}

pub fn save_state_to_dir(dir: &Path, state: &Value) -> Result<(), String> {
    fs::create_dir_all(dir)
        .map_err(|err| format!("failed to create app data dir {}: {err}", dir.display()))?;
    let path = dir.join(STATE_FILE);
    let raw =
        serde_json::to_string(state).map_err(|err| format!("failed to encode state: {err}"))?;
    fs::write(&path, raw)
        .map_err(|err| format!("failed to write state file {}: {err}", path.display()))
}

pub fn clear_state_in_dir(dir: &Path) -> Result<(), String> {
    let path = dir.join(STATE_FILE);
    if path.exists() {
        fs::remove_file(&path)
            .map_err(|err| format!("failed to delete state file {}: {err}", path.display()))?;
    }
    Ok(())
}

pub fn export_to_dir(dir: &Path, filename: &str, content: &str) -> Result<PathBuf, String> {
    let safe_name = sanitize_filename(filename)?;
    let export_dir = dir.join(EXPORT_DIR);
    fs::create_dir_all(&export_dir).map_err(|err| {
        format!(
            "failed to create export directory {}: {err}",
            export_dir.display()
        )
    })?;
    let path = export_dir.join(safe_name);
    fs::write(&path, content)
        .map_err(|err| format!("failed to write export file {}: {err}", path.display()))?;
    Ok(path)
}

pub fn app_data_dir(app: &AppHandle) -> Result<PathBuf, String> {
    app.path()
        .app_data_dir()
        .map_err(|err| format!("failed to resolve app data dir: {err}"))
}

fn sanitize_filename(filename: &str) -> Result<String, String> {
    let trimmed = filename.trim();
    if trimmed.is_empty() || trimmed.contains('/') || trimmed.contains('\\') || trimmed == "." {
        return Err("filename must be a simple relative name".to_string());
    }
    Ok(trimmed.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn state_round_trips() {
        let temp = tempfile::tempdir().unwrap();
        let state = serde_json::json!({"version": 3, "trial": null});

        save_state_to_dir(temp.path(), &state).unwrap();
        assert_eq!(load_state_from_dir(temp.path()).unwrap(), Some(state));
        clear_state_in_dir(temp.path()).unwrap();
        assert_eq!(load_state_from_dir(temp.path()).unwrap(), None);
    }

    #[test]
    fn export_rejects_path_traversal() {
        let temp = tempfile::tempdir().unwrap();

        assert!(export_to_dir(temp.path(), "../bad.json", "{}").is_err());
        let path = export_to_dir(temp.path(), "pitgpt.json", "{}").unwrap();
        assert!(path.exists());
    }
}

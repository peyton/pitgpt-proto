use crate::models::TrialTemplate;

const TEMPLATES_JSON: &str = include_str!("../../shared/trial_templates.json");

pub fn load_templates() -> Result<Vec<TrialTemplate>, String> {
    serde_json::from_str(TEMPLATES_JSON).map_err(|err| format!("invalid shared templates: {err}"))
}

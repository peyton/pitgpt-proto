use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Condition {
    A,
    B,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum YesNo {
    Yes,
    No,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Adherence {
    Yes,
    Partial,
    No,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Protocol {
    pub template: Option<String>,
    pub duration_weeks: u32,
    pub block_length_days: u32,
    pub cadence: String,
    pub washout: String,
    pub primary_outcome_question: String,
    #[serde(default)]
    pub screening: String,
    #[serde(default)]
    pub warnings: String,
    #[serde(default)]
    pub outcome_anchor_low: String,
    #[serde(default)]
    pub outcome_anchor_mid: String,
    #[serde(default)]
    pub outcome_anchor_high: String,
    #[serde(default)]
    pub condition_a_instructions: String,
    #[serde(default)]
    pub condition_b_instructions: String,
    #[serde(default)]
    pub suggested_confounders: Vec<String>,
    #[serde(default)]
    pub clinician_note: String,
    #[serde(default)]
    pub readiness_checklist: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TrialTemplate {
    pub id: String,
    pub icon: String,
    pub name: String,
    pub description: String,
    pub query: String,
    #[serde(rename = "condition_a_placeholder")]
    pub condition_a_placeholder: String,
    #[serde(rename = "condition_b_placeholder")]
    pub condition_b_placeholder: String,
    pub protocol: Protocol,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Assignment {
    pub period_index: u32,
    pub pair_index: u32,
    pub condition: Condition,
    pub start_day: u32,
    pub end_day: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AnalysisProtocol {
    #[serde(default = "default_planned_days")]
    pub planned_days: u32,
    #[serde(default = "default_block_length_days")]
    pub block_length_days: u32,
    #[serde(default = "default_minimum_meaningful_difference")]
    pub minimum_meaningful_difference: f64,
}

impl AnalysisProtocol {
    pub fn planned_days_defaulted(value: &Value) -> bool {
        !value
            .as_object()
            .map(|obj| obj.contains_key("planned_days"))
            .unwrap_or(false)
    }
}

pub fn default_planned_days() -> u32 {
    42
}

pub fn default_block_length_days() -> u32 {
    7
}

pub fn default_minimum_meaningful_difference() -> f64 {
    0.5
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Observation {
    pub day_index: u32,
    pub date: String,
    pub condition: Condition,
    pub primary_score: Option<f64>,
    #[serde(default = "default_yes_no_no")]
    pub irritation: YesNo,
    #[serde(default = "default_adherence_yes")]
    pub adherence: Adherence,
    #[serde(default)]
    pub note: String,
    #[serde(default = "default_yes_no_no")]
    pub is_backfill: YesNo,
    #[serde(default)]
    pub backfill_days: Option<f64>,
}

fn default_yes_no_no() -> YesNo {
    YesNo::No
}

fn default_adherence_yes() -> Adherence {
    Adherence::Yes
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BlockBreakdown {
    pub block_index: u32,
    pub condition: String,
    pub mean: f64,
    pub n: usize,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PairedBlockEstimate {
    pub difference: Option<f64>,
    pub ci_lower: Option<f64>,
    pub ci_upper: Option<f64>,
    pub n_pairs: usize,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SensitivityResult {
    pub difference: Option<f64>,
    pub ci_lower: Option<f64>,
    pub ci_upper: Option<f64>,
    pub n_used_a: usize,
    pub n_used_b: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum QualityGrade {
    A,
    B,
    C,
    D,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AnalysisMethod {
    Welch,
    PairedBlocks,
    InsufficientData,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Verdict {
    FavorsA,
    FavorsB,
    Inconclusive,
    InsufficientData,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ResultCard {
    pub quality_grade: QualityGrade,
    pub verdict: Verdict,
    pub analysis_method: AnalysisMethod,
    pub mean_a: Option<f64>,
    pub mean_b: Option<f64>,
    pub difference: Option<f64>,
    pub ci_lower: Option<f64>,
    pub ci_upper: Option<f64>,
    pub cohens_d: Option<f64>,
    pub paired_block: Option<PairedBlockEstimate>,
    pub n_used_a: usize,
    pub n_used_b: usize,
    pub adherence_rate: f64,
    pub days_logged_pct: f64,
    pub early_stop: bool,
    pub late_backfill_excluded: usize,
    pub block_breakdown: Vec<BlockBreakdown>,
    pub sensitivity_excluding_partial: Option<SensitivityResult>,
    pub planned_days_defaulted: bool,
    pub minimum_meaningful_difference: f64,
    pub meets_minimum_meaningful_effect: Option<bool>,
    pub data_warnings: Vec<String>,
    pub summary: String,
    pub caveats: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ProviderKind {
    Openrouter,
    Ollama,
    ClaudeCli,
    CodexCli,
    ChatgptCli,
    IosOnDevice,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ProviderStatus {
    Available,
    InstalledUnavailable,
    NotFound,
    UnsupportedPlatform,
    Reserved,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProviderInfo {
    pub kind: ProviderKind,
    pub label: String,
    pub status: ProviderStatus,
    pub is_local: bool,
    pub is_offline: bool,
    #[serde(default)]
    pub models: Vec<String>,
    #[serde(default)]
    pub detail: String,
}

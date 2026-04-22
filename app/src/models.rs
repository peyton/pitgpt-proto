use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
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

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AdverseEventSeverity {
    Mild,
    Moderate,
    Severe,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OutcomeDefinition {
    pub id: String,
    pub label: String,
    #[serde(default)]
    pub scale_min: f64,
    #[serde(default = "default_scale_max")]
    pub scale_max: f64,
    #[serde(default = "default_true")]
    pub higher_is_better: bool,
    #[serde(default)]
    pub description: String,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OutcomeRole {
    #[default]
    Primary,
    Secondary,
    Exploratory,
    Safety,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OutcomeMeasure {
    pub id: String,
    pub label: String,
    #[serde(default)]
    pub scale_min: f64,
    #[serde(default = "default_scale_max")]
    pub scale_max: f64,
    #[serde(default = "default_true")]
    pub higher_is_better: bool,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub role: OutcomeRole,
    #[serde(default)]
    pub concept_of_interest: String,
    #[serde(default)]
    pub context_of_use: String,
    #[serde(default = "default_recall_period")]
    pub recall_period: String,
    #[serde(default)]
    pub scoring_instructions: String,
    #[serde(default)]
    pub anchor_low: String,
    #[serde(default)]
    pub anchor_mid: String,
    #[serde(default)]
    pub anchor_high: String,
    #[serde(default = "default_minimum_meaningful_difference")]
    pub minimum_meaningful_difference_positive: f64,
    #[serde(default = "default_minimum_meaningful_difference")]
    pub minimum_meaningful_difference_negative: f64,
    #[serde(default)]
    pub reliability_notes: String,
}

fn default_scale_max() -> f64 {
    10.0
}

fn default_true() -> bool {
    true
}

fn default_recall_period() -> String {
    "today".to_string()
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProtocolAmendment {
    pub date: String,
    pub field: String,
    #[serde(default)]
    pub old_value: String,
    #[serde(default)]
    pub new_value: String,
    pub reason: String,
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
    pub condition_a_label: String,
    #[serde(default)]
    pub condition_b_label: String,
    #[serde(default)]
    pub condition_a_instructions: String,
    #[serde(default)]
    pub condition_b_instructions: String,
    #[serde(default)]
    pub primary_outcome: Option<OutcomeMeasure>,
    #[serde(default)]
    pub secondary_outcomes: Vec<OutcomeDefinition>,
    #[serde(default)]
    pub amendments: Vec<ProtocolAmendment>,
    #[serde(default)]
    pub suggested_confounders: Vec<String>,
    #[serde(default)]
    pub clinician_note: String,
    #[serde(default)]
    pub readiness_checklist: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum IntercurrentEventStrategy {
    TreatmentPolicy,
    WhileOnTreatment,
    CompositeSafety,
    ExcludeInvalid,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct IntercurrentEventStrategySpec {
    pub event: String,
    pub strategy: IntercurrentEventStrategy,
    #[serde(default)]
    pub rationale: String,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DenominatorPolicy {
    #[default]
    PlannedDays,
    EligibleDays,
    ObservedDays,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PrimaryEstimand {
    #[serde(default = "default_estimand_id")]
    pub estimand_id: String,
    #[serde(default = "default_treatment_contrast")]
    pub treatment_contrast: String,
    #[serde(default = "default_outcome_id")]
    pub outcome_id: String,
    #[serde(default = "default_summary_measure")]
    pub summary_measure: String,
    #[serde(default = "default_population_scope")]
    pub population_scope: String,
    #[serde(default = "default_intercurrent_event_strategies")]
    pub intercurrent_event_strategies: Vec<IntercurrentEventStrategySpec>,
}

impl Default for PrimaryEstimand {
    fn default() -> Self {
        Self {
            estimand_id: default_estimand_id(),
            treatment_contrast: default_treatment_contrast(),
            outcome_id: default_outcome_id(),
            summary_measure: default_summary_measure(),
            population_scope: default_population_scope(),
            intercurrent_event_strategies: default_intercurrent_event_strategies(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AnalysisPlan {
    #[serde(default = "default_plan_id")]
    pub plan_id: String,
    #[serde(default = "default_method_version")]
    pub method_version: String,
    #[serde(default = "default_primary_method")]
    pub primary_method: AnalysisMethod,
    #[serde(default = "default_fallback_method")]
    pub fallback_method: AnalysisMethod,
    #[serde(default)]
    pub denominator_policy: DenominatorPolicy,
    #[serde(default)]
    pub estimand: PrimaryEstimand,
    #[serde(default = "default_sensitivity_methods")]
    pub sensitivity_methods: Vec<String>,
    #[serde(default = "default_equivalence_margin_source")]
    pub equivalence_margin_source: String,
    #[serde(default = "default_true")]
    pub pre_specified: bool,
}

impl Default for AnalysisPlan {
    fn default() -> Self {
        Self {
            plan_id: default_plan_id(),
            method_version: default_method_version(),
            primary_method: default_primary_method(),
            fallback_method: default_fallback_method(),
            denominator_policy: DenominatorPolicy::PlannedDays,
            estimand: PrimaryEstimand::default(),
            sensitivity_methods: default_sensitivity_methods(),
            equivalence_margin_source: default_equivalence_margin_source(),
            pre_specified: true,
        }
    }
}

fn default_estimand_id() -> String {
    "primary_ab_mean_difference_v1".to_string()
}

fn default_treatment_contrast() -> String {
    "Condition A minus Condition B".to_string()
}

fn default_outcome_id() -> String {
    "primary_score".to_string()
}

fn default_summary_measure() -> String {
    "paired period mean difference".to_string()
}

fn default_population_scope() -> String {
    "single participant under the locked protocol".to_string()
}

fn default_intercurrent_event_strategies() -> Vec<IntercurrentEventStrategySpec> {
    vec![
        IntercurrentEventStrategySpec {
            event: "missed_or_no_adherence".to_string(),
            strategy: IntercurrentEventStrategy::WhileOnTreatment,
            rationale: "Rows with adherence=no are excluded from efficacy analysis.".to_string(),
        },
        IntercurrentEventStrategySpec {
            event: "late_backfill".to_string(),
            strategy: IntercurrentEventStrategy::ExcludeInvalid,
            rationale: "Rows backfilled after the allowed window are excluded from efficacy analysis.".to_string(),
        },
        IntercurrentEventStrategySpec {
            event: "adverse_event_or_early_stop".to_string(),
            strategy: IntercurrentEventStrategy::CompositeSafety,
            rationale: "Safety events are retained in safety summaries even when efficacy rows are excluded.".to_string(),
        },
    ]
}

fn default_plan_id() -> String {
    "pitgpt-ab-methodology-v1".to_string()
}

fn default_method_version() -> String {
    "2026-04-14-paired-primary-v1".to_string()
}

fn default_primary_method() -> AnalysisMethod {
    AnalysisMethod::PairedBlocks
}

fn default_fallback_method() -> AnalysisMethod {
    AnalysisMethod::Welch
}

fn default_sensitivity_methods() -> Vec<String> {
    vec![
        "welch_daily_mean".to_string(),
        "exclude_partial_adherence".to_string(),
        "missing_data_bounds".to_string(),
        "leave_one_pair_out".to_string(),
    ]
}

fn default_equivalence_margin_source() -> String {
    "minimum_meaningful_difference".to_string()
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
pub struct WorkflowUiMeta {
    pub subtitle: String,
    pub description: String,
    pub hero_asset: String,
    pub theme: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WorkflowDemo {
    pub query: String,
    #[serde(default)]
    pub documents: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WorkflowDefinition {
    pub id: String,
    pub title: String,
    pub objective: String,
    pub prompt_scaffold: String,
    pub recommended_provider: ProviderKind,
    #[serde(default)]
    pub recommended_models: BTreeMap<String, String>,
    pub ui: WorkflowUiMeta,
    pub demo: WorkflowDemo,
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
    #[serde(default)]
    pub condition_a_label: String,
    #[serde(default)]
    pub condition_b_label: String,
    #[serde(default)]
    pub primary_outcome: Option<OutcomeMeasure>,
    #[serde(default)]
    pub secondary_outcomes: Vec<OutcomeDefinition>,
    #[serde(default)]
    pub amendments: Vec<ProtocolAmendment>,
    #[serde(default)]
    pub analysis_plan: AnalysisPlan,
    #[serde(default = "default_timezone")]
    pub timezone: String,
    #[serde(default)]
    pub planned_checkin_time: String,
    #[serde(default = "default_max_backfill_days")]
    pub max_backfill_days: f64,
    #[serde(default)]
    pub condition_a_adherence_criteria: String,
    #[serde(default)]
    pub condition_b_adherence_criteria: String,
}

impl AnalysisProtocol {
    pub fn planned_days_defaulted(value: &Value) -> bool {
        !value
            .as_object()
            .map(|obj| obj.contains_key("planned_days"))
            .unwrap_or(false)
    }
}

fn default_timezone() -> String {
    "local".to_string()
}

fn default_max_backfill_days() -> f64 {
    2.0
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
    #[serde(default)]
    pub observation_id: String,
    pub day_index: u32,
    pub date: String,
    pub condition: Condition,
    #[serde(default)]
    pub assigned_condition: Option<Condition>,
    #[serde(default)]
    pub actual_condition: Option<Condition>,
    pub primary_score: Option<f64>,
    #[serde(default = "default_yes_no_no")]
    pub irritation: YesNo,
    #[serde(default = "default_adherence_yes")]
    pub adherence: Adherence,
    #[serde(default)]
    pub adherence_reason: String,
    #[serde(default)]
    pub note: String,
    #[serde(default = "default_yes_no_no")]
    pub is_backfill: YesNo,
    #[serde(default)]
    pub backfill_days: Option<f64>,
    #[serde(default)]
    pub adverse_event_severity: Option<AdverseEventSeverity>,
    #[serde(default)]
    pub adverse_event_description: String,
    #[serde(default)]
    pub secondary_scores: BTreeMap<String, f64>,
    #[serde(default)]
    pub recorded_at: String,
    #[serde(default)]
    pub timezone: String,
    #[serde(default)]
    pub planned_checkin_time: String,
    #[serde(default)]
    pub minutes_from_planned_checkin: Option<i32>,
    #[serde(default)]
    pub exposure_start_at: String,
    #[serde(default)]
    pub exposure_end_at: String,
    #[serde(default)]
    pub measurement_timing: String,
    #[serde(default)]
    pub deviation_codes: Vec<String>,
    #[serde(default)]
    pub confounders: BTreeMap<String, String>,
    #[serde(default)]
    pub rescue_action: String,
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
    pub randomization_p_value: Option<f64>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SensitivityResult {
    pub difference: Option<f64>,
    pub ci_lower: Option<f64>,
    pub ci_upper: Option<f64>,
    pub n_used_a: usize,
    pub n_used_b: usize,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SensitivityAnalysisResult {
    pub name: String,
    pub method: String,
    #[serde(default)]
    pub summary: String,
    pub difference: Option<f64>,
    pub ci_lower: Option<f64>,
    pub ci_upper: Option<f64>,
    pub n_used_a: usize,
    pub n_used_b: usize,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SecondaryOutcomeResult {
    pub outcome_id: String,
    pub label: String,
    pub mean_a: Option<f64>,
    pub mean_b: Option<f64>,
    pub difference: Option<f64>,
    pub n_used_a: usize,
    pub n_used_b: usize,
    pub summary: String,
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

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ActionabilityClass {
    Switch,
    KeepCurrent,
    RepeatWithBetterControls,
    StopForSafety,
    InconclusiveNoAction,
    InsufficientData,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TrialLock {
    #[serde(default)]
    pub protocol_hash: String,
    #[serde(default)]
    pub analysis_plan_hash: String,
    #[serde(default)]
    pub schedule_hash: String,
    #[serde(default)]
    pub estimand_hash: String,
    #[serde(default)]
    pub locked_at: String,
    #[serde(default = "default_hash_algorithm")]
    pub hash_algorithm: String,
}

impl Default for TrialLock {
    fn default() -> Self {
        Self {
            protocol_hash: String::new(),
            analysis_plan_hash: String::new(),
            schedule_hash: String::new(),
            estimand_hash: String::new(),
            locked_at: String::new(),
            hash_algorithm: default_hash_algorithm(),
        }
    }
}

fn default_hash_algorithm() -> String {
    "sha256".to_string()
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RowExclusion {
    pub day_index: u32,
    #[serde(default)]
    pub date: String,
    #[serde(default)]
    pub condition: Option<Condition>,
    pub reason: String,
    #[serde(default = "default_true")]
    pub safety_retained: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AnalysisDatasetSnapshot {
    pub rows_total: usize,
    pub rows_used_primary: usize,
    pub rows_used_safety: usize,
    pub rows_excluded_primary: usize,
    #[serde(default)]
    pub exclusions: Vec<RowExclusion>,
    #[serde(default)]
    pub denominator_policy: DenominatorPolicy,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MethodsAppendix {
    #[serde(default = "default_method_version")]
    pub method_version: String,
    #[serde(default)]
    pub estimand: PrimaryEstimand,
    #[serde(default)]
    pub analysis_plan: AnalysisPlan,
    #[serde(default)]
    pub trial_lock: TrialLock,
    #[serde(default)]
    pub input_hashes: BTreeMap<String, String>,
    #[serde(default)]
    pub sensitivity_methods: Vec<String>,
    #[serde(default)]
    pub row_exclusion_reasons: Vec<String>,
    #[serde(default)]
    pub software_versions: BTreeMap<String, String>,
    #[serde(default = "default_true")]
    pub pre_specified: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ValidationReport {
    pub valid: bool,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
    pub observation_count: usize,
    pub planned_days: Option<u32>,
    pub block_length_days: Option<u32>,
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
    pub relative_change_pct: Option<f64>,
    pub paired_block: Option<PairedBlockEstimate>,
    pub welch_sensitivity: Option<SensitivityAnalysisResult>,
    pub n_used_a: usize,
    pub n_used_b: usize,
    pub adherence_rate: f64,
    pub days_logged_pct: f64,
    pub early_stop: bool,
    pub late_backfill_excluded: usize,
    pub adverse_event_count: usize,
    pub adverse_event_by_severity: BTreeMap<String, usize>,
    pub block_breakdown: Vec<BlockBreakdown>,
    pub sensitivity_excluding_partial: Option<SensitivityResult>,
    pub sensitivity_analyses: Vec<SensitivityAnalysisResult>,
    pub secondary_outcomes: Vec<SecondaryOutcomeResult>,
    pub protocol_amendment_count: usize,
    pub planned_days_defaulted: bool,
    pub minimum_meaningful_difference: f64,
    pub meets_minimum_meaningful_effect: Option<bool>,
    pub equivalence_margin: Option<f64>,
    pub supports_no_meaningful_difference: Option<bool>,
    pub randomization_p_value: Option<f64>,
    pub actionability: ActionabilityClass,
    pub harm_benefit_summary: String,
    pub reliability_warnings: Vec<String>,
    pub dataset_snapshot: AnalysisDatasetSnapshot,
    pub methods_appendix: MethodsAppendix,
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

mod analysis;
mod commands;
mod ingestion;
mod models;
mod notifications;
mod providers;
mod schedule;
mod storage;
mod templates;

pub use analysis::analyze_result;
pub use commands::*;
pub use models::*;
pub use providers::discover_provider_infos;
pub use schedule::generate_schedule_result;
pub use templates::load_templates;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .invoke_handler(tauri::generate_handler![
            commands::get_templates,
            commands::generate_schedule,
            commands::plan_trial_reminders,
            commands::analyze,
            commands::analyze_example,
            commands::load_app_state,
            commands::save_app_state,
            commands::clear_app_state,
            commands::export_file,
            commands::discover_ai_tools,
            commands::ingest_local,
        ])
        .run(tauri::generate_context!())
        .expect("error while running PitGPT Tauri app");
}

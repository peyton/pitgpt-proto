import { useApp } from "../lib/AppContext";
import { InfoTooltip } from "../components/InfoTooltip";
import { clearAllData, downloadFile, exportCSV, exportJSON } from "../lib/storage";
import { loadState } from "../lib/storage";

export function Settings() {
  const { state, updateSettings, clearAll } = useApp();
  const { settings } = state;

  const handleExportCSV = () => {
    const all = state.completedResults.flatMap((r) => r.trial.observations);
    if (state.trial) all.push(...state.trial.observations);
    downloadFile(exportCSV(all), "pitgpt-export.csv", "text/csv");
  };

  const handleExportJSON = () => {
    downloadFile(exportJSON(state), "pitgpt-export.json", "application/json");
  };

  const handleDelete = () => {
    if (!confirm("Permanently delete ALL data? This cannot be undone.")) return;
    clearAllData();
    clearAll();
  };

  const storageSize = new Blob([JSON.stringify(loadState())]).size;
  const sizeLabel = storageSize < 1024 ? `${storageSize} B` : `~${Math.round(storageSize / 1024)} KB`;

  return (
    <div className="page-container" style={{ maxWidth: 640 }}>
      <h1 className="fade-up" style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-.5px", marginBottom: 32 }}>Settings</h1>

      <div className="settings-section fade-up fade-up-1">
        <h2>Reminders</h2>
        <div className="setting-row">
          <div className="setting-label">
            <h3>Daily Reminder <InfoTooltip text="Get a notification at your chosen time to complete your daily check-in. Consistency improves your data quality grade." /></h3>
            <p>In-app banner at your chosen time</p>
          </div>
          <button
            className={`toggle${settings.reminderEnabled ? " on" : ""}`}
            onClick={() => updateSettings({ reminderEnabled: !settings.reminderEnabled })}
            aria-label="Toggle daily reminder"
          />
        </div>
        <div className="setting-row">
          <div className="setting-label">
            <h3>Reminder Time</h3>
            <p>When should we nudge you?</p>
          </div>
          <input
            type="time"
            className="time-input"
            value={settings.reminderTime}
            onChange={(e) => updateSettings({ reminderTime: e.target.value })}
          />
        </div>
        <div className="setting-row">
          <div className="setting-label">
            <h3>Email Reminders <InfoTooltip text="Optional backup reminder via email. Stored locally and never shared." /></h3>
            <p>Backup notification via email</p>
          </div>
          <button
            className={`toggle${settings.emailReminderEnabled ? " on" : ""}`}
            onClick={() => updateSettings({ emailReminderEnabled: !settings.emailReminderEnabled })}
            aria-label="Toggle email reminder"
          />
        </div>
      </div>

      <div className="settings-section fade-up fade-up-2">
        <h2>Data &amp; Privacy</h2>
        <div className="setting-row">
          <div className="setting-label">
            <h3>Export All Data</h3>
            <p>Download all your trial data as CSV or JSON</p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-s btn-sm" onClick={handleExportCSV}>CSV</button>
            <button className="btn btn-s btn-sm" onClick={handleExportJSON}>JSON</button>
          </div>
        </div>
        <div className="setting-row">
          <div className="setting-label">
            <h3>Storage <InfoTooltip text="All data is stored locally on your device. Nothing is sent to a server. You are the only person who can see your experiments." /></h3>
            <p>All data stored locally on this device</p>
          </div>
          <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--gray-400)" }}>{sizeLabel} used</span>
        </div>
      </div>

      <div className="settings-section fade-up fade-up-3">
        <h2>About</h2>
        <div className="setting-row">
          <div className="setting-label">
            <h3>Version</h3>
            <p>PitGPT v1.0 — Personal Experiment Engine</p>
          </div>
          <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--gray-400)" }}>v1.0.0</span>
        </div>
        <div className="setting-row">
          <div className="setting-label">
            <h3>Privacy</h3>
            <p>No analytics, no trackers, no third-party data sharing</p>
          </div>
          <span className="badge badge-safe" style={{ fontSize: 10 }}>Private</span>
        </div>
      </div>

      <div className="danger-zone fade-up fade-up-4">
        <h3>Danger Zone</h3>
        <p>Permanently delete all your data, including all trials, check-ins, and results. This action cannot be undone.</p>
        <button className="btn btn-d btn-sm" onClick={handleDelete}>Delete All Data</button>
      </div>
    </div>
  );
}

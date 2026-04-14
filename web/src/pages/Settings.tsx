import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { useApp } from "../lib/AppContext";
import { healthCheck } from "../lib/api";
import { InfoTooltip } from "../components/InfoTooltip";
import { clearAllData, downloadFile, exportCSV, exportJSON, loadState, restoreStateFromJSON } from "../lib/storage";

type ApiStatus = "checking" | "online" | "offline";

export function Settings() {
  const { state, updateSettings, restoreAll, clearAll } = useApp();
  const { settings } = state;
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [importError, setImportError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const importInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    void healthCheck().then((ok) => {
      if (active) setApiStatus(ok ? "online" : "offline");
    });
    return () => {
      active = false;
    };
  }, []);

  const handleExportCSV = () => {
    const all = state.completedResults.flatMap((r) => r.trial.observations);
    if (state.trial) all.push(...state.trial.observations);
    downloadFile(exportCSV(all), "pitgpt-export.csv", "text/csv");
  };

  const handleExportJSON = () => {
    downloadFile(exportJSON(state), "pitgpt-export.json", "application/json");
  };

  const handleImport = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        restoreAll(restoreStateFromJSON(String(reader.result ?? "")));
        setImportError(null);
      } catch (error) {
        setImportError(error instanceof Error ? error.message : "Could not import that file.");
      } finally {
        event.target.value = "";
      }
    };
    reader.onerror = () => setImportError("Could not read that file.");
    reader.readAsText(file);
  };

  const handleDelete = () => {
    clearAllData();
    clearAll();
    setShowDeleteConfirm(false);
  };

  const storageSize = new Blob([JSON.stringify(loadState())]).size;
  const sizeLabel = storageSize < 1024 ? `${storageSize} B` : `~${Math.round(storageSize / 1024)} KB`;

  return (
    <div className="page-container" style={{ maxWidth: 640 }}>
      <h1 className="fade-up" style={{ fontSize: 30, fontWeight: 800, letterSpacing: 0, marginBottom: 32 }}>Settings</h1>

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
            <h3>Email Reminders <InfoTooltip text="Email delivery is not implemented in this local-first prototype." /></h3>
            <p>Not available in the local prototype</p>
          </div>
          <button
            className="toggle"
            onClick={() => updateSettings({ emailReminderEnabled: false })}
            aria-label="Toggle email reminder"
            disabled
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
            <button className="btn btn-s btn-sm" onClick={() => importInputRef.current?.click()}>Import</button>
          </div>
        </div>
        <input ref={importInputRef} type="file" accept=".json" style={{ display: "none" }} onChange={handleImport} />
        {importError && <p className="form-error" role="alert">{importError}</p>}
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
            <h3>API Status <InfoTooltip text="Protocol generation and analysis use the local API when available." /></h3>
            <p>{getApiStatusCopy(apiStatus)}</p>
          </div>
          <span className={getApiStatusClass(apiStatus)}>{apiStatus}</span>
        </div>
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
        <button className="btn btn-d btn-sm" onClick={() => setShowDeleteConfirm(true)}>Delete All Data</button>
      </div>

      {showDeleteConfirm && (
        <div className="modal-backdrop" role="presentation">
          <div className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="delete-title">
            <h3 id="delete-title">Delete all local data?</h3>
            <p>Trials, check-ins, settings, and completed results will be removed from this browser.</p>
            <div className="modal-actions">
              <button className="btn btn-s" onClick={() => setShowDeleteConfirm(false)}>
                Cancel
              </button>
              <button className="btn btn-d" onClick={handleDelete}>
                Delete All Data
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function getApiStatusCopy(status: ApiStatus): string {
  if (status === "checking") return "Checking local API connection";
  if (status === "online") return "Local API is reachable";
  return "Local API is not reachable";
}

function getApiStatusClass(status: ApiStatus): string {
  if (status === "online") return "badge badge-safe";
  if (status === "offline") return "badge badge-caution";
  return "badge badge-neutral";
}

import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../lib/AppContext";
import { analyze } from "../lib/api";
import { InfoTooltip } from "../components/InfoTooltip";
import { sendDueNativeReminder } from "../lib/nativeNotifications";
import type { Trial } from "../lib/types";
import {
  buildObservation,
  buildObservationForDate,
  canBackfill,
  checkAdverseEventStreak,
  addTrialEvent,
  getConditionLabel,
  getCurrentAssignment,
  getDaysLeft,
  getNextCheckInCopy,
  getTrialProgress,
  hasCheckedInToday,
  isTrialComplete,
  protocolToDict,
} from "../lib/trial";

export function ActiveTrial() {
  const { state, addObservation, completeTrial } = useApp();
  const navigate = useNavigate();
  const trial = state.trial;

  const [score, setScore] = useState(5);
  const [irritation, setIrritation] = useState<"yes" | "no">("no");
  const [adherence, setAdherence] = useState<"yes" | "no" | "partial">("yes");
  const [adherenceReason, setAdherenceReason] = useState("");
  const [adverseSeverity, setAdverseSeverity] = useState<"mild" | "moderate" | "severe">("mild");
  const [adverseDescription, setAdverseDescription] = useState("");
  const [secondaryScores, setSecondaryScores] = useState<Record<string, number>>({});
  const [note, setNote] = useState("");
  const [backfillDate, setBackfillDate] = useState("");
  const [backfillScore, setBackfillScore] = useState(5);
  const [backfillIrritation, setBackfillIrritation] = useState<"yes" | "no">("no");
  const [backfillAdherence, setBackfillAdherence] = useState<"yes" | "no" | "partial">("yes");
  const [backfillNote, setBackfillNote] = useState("");
  const [backfillError, setBackfillError] = useState<string | null>(null);
  const [backfillSaved, setBackfillSaved] = useState(false);
  const [noteOpen, setNoteOpen] = useState(false);
  const [backfillOpen, setBackfillOpen] = useState(false);
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    if (!trial || trial.status !== "active") return;
    void sendDueNativeReminder(trial, state.settings.reminderEnabled, state.settings.reminderTime);
  }, [trial, state.settings.reminderEnabled, state.settings.reminderTime]);

  const handleEscape = useCallback((event: KeyboardEvent) => {
    if (event.key === "Escape") setShowStopConfirm(false);
  }, []);

  useEffect(() => {
    if (!showStopConfirm) return;
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [showStopConfirm, handleEscape]);

  if (!trial || trial.status !== "active") {
    return (
      <div className="page-container empty-state-center">
        <div className="empty-state">
          <p>No active trial.</p>
          <button className="btn btn-p" onClick={() => navigate("/")}>Start a New Experiment</button>
        </div>
      </div>
    );
  }

  const progress = getTrialProgress(trial);
  const assignment = getCurrentAssignment(trial);
  const todayDone = hasCheckedInToday(trial) || submitted;
  const trialComplete = isTrialComplete(trial);
  const aeStreak = checkAdverseEventStreak(trial);
  const daysLeft = getDaysLeft(trial);
  const nextCheckIn = getNextCheckInCopy(trial);
  const minimumDataWarning = getMinimumDataWarning(trial);
  const showReminder = shouldShowReminder(state.settings.reminderEnabled, state.settings.reminderTime, todayDone, trialComplete);
  const today = toLocalDateInput(new Date());
  const twoDaysAgo = toLocalDateInput(offsetDate(-2));

  const handleCheckin = () => {
    if (todayDone) return;
    setSubmitting(true);
    const obs = buildObservation(trial, score, irritation, adherence, note, {
      adherenceReason,
      adverseEventSeverity: adverseSeverity,
      adverseEventDescription: adverseDescription,
      secondaryScores,
    });
    addObservation(obs);
    setSubmitted(true);
    setSubmitting(false);
    setScore(5);
    setNote("");
    setIrritation("no");
    setAdherence("yes");
    setAdherenceReason("");
    setAdverseSeverity("mild");
    setAdverseDescription("");
    setSecondaryScores({});
    setNoteOpen(false);
  };

  const handleBackfill = () => {
    setBackfillError(null);
    setBackfillSaved(false);
    if (!backfillDate) {
      setBackfillError("Choose a date from the last 2 days.");
      return;
    }
    if (!canBackfill(trial, backfillDate)) {
      setBackfillError("Backfill is limited to the last 2 days.");
      return;
    }
    if (trial.observations.some((obs) => obs.date === backfillDate)) {
      setBackfillError("That date already has a check-in.");
      return;
    }
    addObservation(
      buildObservationForDate(
        trial,
        backfillDate,
        backfillScore,
        backfillIrritation,
        backfillAdherence,
        backfillNote,
      ),
    );
    setBackfillDate("");
    setBackfillNote("");
    setBackfillIrritation("no");
    setBackfillAdherence("yes");
    setBackfillScore(5);
    setBackfillSaved(true);
  };

  const handleComplete = async () => {
    setAnalyzing(true);
    setAnalysisError(null);
    try {
      const result = await analyze(protocolToDict(trial.protocol), trial.observations);
      const stopped = trialComplete ? trial : addTrialEvent(trial, "trial_stopped", "Stopped before the planned end.");
      const completedTrial = {
        ...addTrialEvent(stopped, "trial_analyzed", "Generated result card."),
        status: "completed" as const,
        completedAt: new Date().toISOString(),
      };
      completeTrial({ trial: completedTrial, result });
      navigate("/results");
    } catch (error) {
      setAnalysisError(error instanceof Error ? error.message : "Failed to analyze results. Please try again.");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleStop = () => {
    setShowStopConfirm(true);
  };

  return (
    <div className="page-container">
      {/* Hero */}
      <div className="trial-hero fade-up">
        <div className="trial-hero-top">
          <div>
            <span className="badge badge-safe badge-dot trial-hero-badge">Active</span>
            <h2 className="trial-hero-title">
              {trial.conditionALabel} vs. {trial.conditionBLabel}
            </h2>
            <p className="trial-hero-meta">
              {trial.protocol.template ?? "Custom"} · {trial.protocol.duration_weeks}w · {daysLeft}d left · {nextCheckIn}
            </p>
          </div>
          <div className="trial-hero-counter">
            <div className="trial-hero-count">
              {Math.min(progress.dayIndex, progress.totalDays)}
            </div>
            <div className="trial-hero-count-label">of {progress.totalDays}</div>
          </div>
        </div>
        <div className="progress-bar">
          <div className="fill" style={{ width: `${Math.min((progress.dayIndex / progress.totalDays) * 100, 100)}%` }} />
        </div>
        <div className="trial-stats">
          <div className="trial-stat">
            <div className="stat-value">{progress.adherenceRate}%</div>
            <div className="stat-label">Adherence</div>
          </div>
          <div className="trial-stat">
            <div className="stat-value">{progress.daysLogged}/{Math.min(progress.dayIndex, progress.totalDays)}</div>
            <div className="stat-label">Days Logged</div>
          </div>
          <div className="trial-stat">
            <div className="stat-value">{progress.adverseEvents}</div>
            <div className="stat-label">Adverse Events</div>
          </div>
        </div>
      </div>

      {/* Trial complete banner */}
      {trialComplete && (
        <div className="trial-complete-banner fade-up fade-up-1">
          <span>Trial complete! Ready to see your results.</span>
          <button className="btn btn-p btn-sm" onClick={handleComplete} disabled={analyzing}>
            {analyzing ? <div className="spinner spinner-sm" /> : "View Results"}
          </button>
        </div>
      )}

      {/* AE Streak Warning */}
      {aeStreak && (
        <div className="safety-stop-banner fade-up fade-up-1">
          <span>Irritation has been logged for 3+ consecutive days. Stop for safety before collecting more data.</span>
          <button className="btn btn-d btn-sm" onClick={handleStop} disabled={analyzing}>
            Stop and Analyze
          </button>
        </div>
      )}

      {analysisError && <p className="form-error" role="alert">{analysisError}</p>}

      {showReminder && (
        <div className="reminder-banner fade-up fade-up-1">
          Daily reminder is due. Log today's check-in when you have a consistent moment.
        </div>
      )}

      {/* Assignment */}
      {assignment && !trialComplete && (
        <div className="assignment-card fade-up fade-up-1">
          <div className="assignment-letter">{assignment.condition}</div>
          <div className="assignment-info">
            <h3>Today's Assignment</h3>
            <p>{getConditionLabel(trial, assignment.condition)}</p>
          </div>
        </div>
      )}

      {/* No Peek Banner */}
      {!trialComplete && (
        <div className="no-peek-banner fade-up fade-up-2">
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
            <path d="M1 10s3-6 9-6 9 6 9 6-3 6-9 6-9-6-9-6z" stroke="currentColor" strokeWidth="1.5" />
            <circle cx="10" cy="10" r="3" stroke="currentColor" strokeWidth="1.5" />
            <path d="M3 17L17 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          No mid-trial comparisons are shown. This prevents bias in your daily ratings.
          <InfoTooltip text="If you saw 'A is winning' partway through, you'd unconsciously rate A higher. Hiding comparisons is what makes this a valid experiment." />
        </div>
      )}

      {/* Check-in */}
      {!trialComplete && (
        <div className="checkin-card fade-up fade-up-3">
          <h3>Daily Check-In <span className="time-est">&lt; 20 seconds</span></h3>

          {todayDone ? (
            <div className="checkin-done">
              <div className="checkin-done-icon">✓</div>
              <p className="checkin-done-title">Check-in submitted</p>
              <p className="checkin-done-sub">Come back tomorrow.</p>
            </div>
          ) : (
            <>
              <div className="form-group">
                <div className="form-label">
                  {trial.protocol.primary_outcome_question || "Satisfaction"}
                  <InfoTooltip text="Rate how your skin looks and feels right now. 0 = worst it's ever been, 10 = best it's ever been." />
                </div>
                <div className="slider-wrap">
                  <div className="slider-anchors">
                    <span>Poor</span>
                    <span>Excellent</span>
                  </div>
                  <input
                    type="range"
                    className="slider-input"
                    min="0"
                    max="10"
                    value={score}
                    onChange={(e) => setScore(Number(e.target.value))}
                    aria-label={`Score: ${score}`}
                  />
                  <div className="slider-ticks">
                    {Array.from({ length: 11 }, (_, i) => (
                      <span key={i}>{i}</span>
                    ))}
                  </div>
                  <div className="slider-value" aria-live="polite">
                    {score}
                  </div>
                </div>
              </div>

              <div className="form-group">
                <div className="form-label">
                  Any irritation or discomfort?
                  <InfoTooltip text="If you report irritation 3+ days in a row, we'll recommend stopping. Your safety matters more than completing the experiment." />
                </div>
                <div className="radio-group">
                  <button className={`radio-pill${irritation === "no" ? " selected" : ""}`} onClick={() => setIrritation("no")}>No</button>
                  <button className={`radio-pill${irritation === "yes" ? " danger-selected" : ""}`} onClick={() => setIrritation("yes")}>Yes</button>
                </div>
              </div>

              <div className="form-group">
                <div className="form-label">Did you use the assigned product today?</div>
                <div className="radio-group">
                  <button className={`radio-pill${adherence === "yes" ? " selected" : ""}`} onClick={() => setAdherence("yes")}>Yes</button>
                  <button className={`radio-pill${adherence === "no" ? " selected" : ""}`} onClick={() => setAdherence("no")}>No</button>
                  <button className={`radio-pill${adherence === "partial" ? " selected" : ""}`} onClick={() => setAdherence("partial")}>Partial</button>
                </div>
              </div>

              {adherence !== "yes" && (
                <div className="form-group">
                  <label className="form-label" htmlFor="adherence-reason">What got in the way?</label>
                  <input
                    id="adherence-reason"
                    className="text-input"
                    value={adherenceReason}
                    onChange={(e) => setAdherenceReason(e.target.value)}
                    placeholder="Forgot, ran out, travel, timing did not work..."
                  />
                </div>
              )}

              {irritation === "yes" && (
                <div className="adverse-event-box">
                  <div className="form-label">Discomfort details</div>
                  <select
                    className="time-input select-input"
                    value={adverseSeverity}
                    onChange={(e) => setAdverseSeverity(e.target.value as "mild" | "moderate" | "severe")}
                    aria-label="Discomfort severity"
                  >
                    <option value="mild">Mild</option>
                    <option value="moderate">Moderate</option>
                    <option value="severe">Severe</option>
                  </select>
                  <textarea
                    className="optional-note"
                    placeholder="What happened?"
                    value={adverseDescription}
                    onChange={(e) => setAdverseDescription(e.target.value)}
                    aria-label="Discomfort description"
                  />
                </div>
              )}

              {(trial.protocol.secondary_outcomes?.length ?? 0) > 0 && (
                <details className="inline-disclosure">
                  <summary>Secondary outcomes</summary>
                  <div className="secondary-score-list">
                    {trial.protocol.secondary_outcomes?.map((outcome) => (
                      <label key={outcome.id} className="secondary-score-row">
                        <span>{outcome.label}</span>
                        <input
                          type="number"
                          className="time-input"
                          min={outcome.scale_min}
                          max={outcome.scale_max}
                          value={secondaryScores[outcome.id] ?? ""}
                          onChange={(event) => {
                            const next = Number(event.target.value);
                            setSecondaryScores((current) => ({
                              ...current,
                              [outcome.id]: Number.isFinite(next) ? next : 0,
                            }));
                          }}
                          aria-label={`Secondary outcome ${outcome.label}`}
                        />
                      </label>
                    ))}
                  </div>
                </details>
              )}

              <details className="inline-disclosure" open={noteOpen} onToggle={(event) => setNoteOpen(event.currentTarget.open)}>
                <summary>
                  Optional note
                  <InfoTooltip text="Log anything that might affect your result: travel, stress, sleep, weather, schedule changes." />
                </summary>
                <textarea
                  className="optional-note"
                  placeholder="Travel, stress, sleep, weather..."
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </details>

              <div className="checkin-submit-row">
                <button className="btn btn-p" onClick={handleCheckin} disabled={submitting}>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M2 8l4 4 8-8" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Submit Check-In
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {!trialComplete && (
        <div className="trial-stop-actions">
          <button className="btn btn-d btn-sm" onClick={handleStop} disabled={analyzing}>
            Stop Experiment Early
          </button>
        </div>
      )}

      {!trialComplete && (
        <details className="backfill-card fade-up fade-up-4" open={backfillOpen} onToggle={(event) => setBackfillOpen(event.currentTarget.open)}>
          <summary className="backfill-summary">
            Backfill recent day
            <span>Use only for a missed check-in from the last 2 days.</span>
          </summary>
          <div className="backfill-card-header">
            <div />
            <div className="backfill-header-actions">
              <input
                type="date"
                className="time-input date-input"
                min={twoDaysAgo}
                max={today}
                value={backfillDate}
                onChange={(e) => {
                  setBackfillDate(e.target.value);
                  setBackfillError(null);
                  setBackfillSaved(false);
                  e.currentTarget.blur();
                }}
                aria-label="Backfill date"
              />
              <button className="btn btn-s btn-sm" onClick={handleBackfill}>
                Add Backfill
              </button>
            </div>
          </div>
          <div className="backfill-grid">
            <label>
              Score
              <input
                type="range"
                className="slider-input"
                min="0"
                max="10"
                value={backfillScore}
                onChange={(e) => setBackfillScore(Number(e.target.value))}
                aria-label="Backfill score"
              />
              <span className="backfill-score">{backfillScore}</span>
            </label>
            <div>
              <div className="form-label">Irritation?</div>
              <select
                className="time-input select-input"
                value={backfillIrritation}
                onChange={(e) => setBackfillIrritation(e.target.value as "yes" | "no")}
                aria-label="Backfill irritation"
              >
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </select>
            </div>
            <div>
              <div className="form-label">Adherence</div>
              <select
                className="time-input select-input"
                value={backfillAdherence}
                onChange={(e) => setBackfillAdherence(e.target.value as "yes" | "no" | "partial")}
                aria-label="Backfill adherence"
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
                <option value="partial">Partial</option>
              </select>
            </div>
          </div>
          <textarea
            className="optional-note"
            placeholder="Optional backfill note..."
            value={backfillNote}
            onChange={(e) => setBackfillNote(e.target.value)}
            aria-label="Backfill note"
          />
          {backfillError && <p className="form-error" role="alert">{backfillError}</p>}
          {backfillSaved && <p className="form-success" role="status">Backfill saved.</p>}
        </details>
      )}

      {showStopConfirm && (
        <div className="modal-backdrop" role="presentation">
          <div className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="stop-title">
            <h3 id="stop-title">Stop this trial?</h3>
            <p>
              Your existing check-ins stay saved. PitGPT will analyze the data as an early stop and label the caveats clearly.
            </p>
            {minimumDataWarning && (
              <p className="caution-text">{minimumDataWarning}</p>
            )}
            <div className="modal-actions">
              <button className="btn btn-s" onClick={() => setShowStopConfirm(false)} disabled={analyzing}>
                Keep Going
              </button>
              <button className="btn btn-d" onClick={handleComplete} disabled={analyzing}>
                {analyzing ? <div className="spinner spinner-sm" /> : "Stop and Analyze"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function getMinimumDataWarning(trial: Trial): string | null {
  const scoredA = trial.observations.filter((obs) => obs.condition === "A" && obs.primary_score != null).length;
  const scoredB = trial.observations.filter((obs) => obs.condition === "B" && obs.primary_score != null).length;
  if (scoredA < 2 || scoredB < 2) {
    return "There is not enough data from both conditions for a reliable comparison yet. The result will be marked as insufficient if you stop now.";
  }
  return null;
}

function offsetDate(offsetDays: number): Date {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  return date;
}

function toLocalDateInput(date: Date): string {
  const local = new Date(date);
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
  return local.toISOString().slice(0, 10);
}

function shouldShowReminder(
  enabled: boolean,
  reminderTime: string,
  todayDone: boolean,
  trialComplete: boolean,
): boolean {
  if (!enabled || todayDone || trialComplete) return false;
  const [hourText, minuteText] = reminderTime.split(":");
  const hour = Number(hourText);
  const minute = Number(minuteText);
  if (Number.isNaN(hour) || Number.isNaN(minute)) return false;
  const now = new Date();
  const due = new Date();
  due.setHours(hour, minute, 0, 0);
  return now >= due;
}

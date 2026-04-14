import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../lib/AppContext";
import { InfoTooltip } from "../components/InfoTooltip";
import { doctorQuestions, exportAppointmentBrief } from "../lib/brief";
import { downloadFile, exportCSV } from "../lib/storage";
import { computeTrialAuditHash } from "../lib/trial";
import type { CompletedTrial, Observation } from "../lib/types";

const safetyBadgeClass: Record<string, string> = {
  GREEN: "badge badge-safe badge-dot",
  YELLOW: "badge badge-caution badge-dot",
  RED: "badge badge-danger badge-dot",
};

const safetyLabel: Record<string, string> = {
  GREEN: "Green",
  YELLOW: "Yellow",
  RED: "Red",
};

const evidenceClass: Record<string, string> = {
  strong: "badge badge-safe",
  moderate: "badge badge-info",
  weak: "badge badge-neutral",
  novel: "badge badge-pink",
};

function TimeSeriesChart({ observations, condALabel, condBLabel }: {
  observations: Observation[];
  condALabel: string;
  condBLabel: string;
}) {
  const scored = observations.filter((o) => o.primary_score !== null).sort((a, b) => a.day_index - b.day_index);
  if (scored.length === 0) return <p style={{ color: "var(--gray-400)", textAlign: "center", padding: 40 }}>No data to chart.</p>;

  const width = 760;
  const height = 200;
  const padLeft = 30;
  const padRight = 10;
  const padTop = 10;
  const padBottom = 25;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const maxDay = Math.max(...scored.map((o) => o.day_index));
  const xScale = (day: number) => padLeft + ((day - 1) / Math.max(maxDay - 1, 1)) * plotW;
  const yScale = (val: number) => padTop + plotH - (val / 10) * plotH;

  const aPoints = scored.filter((o) => o.condition === "A");
  const bPoints = scored.filter((o) => o.condition === "B");

  const polyline = (pts: Observation[]) =>
    pts.map((o) => `${xScale(o.day_index).toFixed(0)},${yScale(o.primary_score!).toFixed(0)}`).join(" ");

  return (
    <div className="chart-card fade-up fade-up-3">
      <div className="chart-header">
        <h3>Daily Scores by Condition</h3>
        <div className="chart-legend">
          <div className="chart-legend-item">
            <div className="chart-legend-dot" style={{ background: "var(--pink-500)" }} />
            {condALabel} (A)
          </div>
          <div className="chart-legend-item">
            <div className="chart-legend-dot" style={{ background: "var(--pink-300)" }} />
            {condBLabel} (B)
          </div>
        </div>
      </div>
      <div className="chart-body">
        <svg className="chart-svg" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
          {/* Grid lines */}
          {[0, 2, 4, 6, 8, 10].map((v) => (
            <g key={v}>
              <line x1={padLeft} y1={yScale(v)} x2={width - padRight} y2={yScale(v)} className="chart-grid-line" strokeDasharray="4,4" />
              <text x={padLeft - 4} y={yScale(v) + 3} className="chart-label" textAnchor="end">{v}</text>
            </g>
          ))}
          {/* Lines */}
          {aPoints.length > 1 && <polyline className="chart-line" stroke="#FF006E" points={polyline(aPoints)} />}
          {bPoints.length > 1 && <polyline className="chart-line" stroke="#FF80B5" points={polyline(bPoints)} />}
          {/* Dots */}
          <g fill="#FF006E">
            {aPoints.map((o) => <circle key={o.day_index} cx={xScale(o.day_index)} cy={yScale(o.primary_score!)} className="chart-dot" />)}
          </g>
          <g fill="#FF80B5">
            {bPoints.map((o) => <circle key={o.day_index} cx={xScale(o.day_index)} cy={yScale(o.primary_score!)} className="chart-dot" />)}
          </g>
        </svg>
      </div>
    </div>
  );
}

function ResultView({ completed }: { completed: CompletedTrial }) {
  const { trial, result } = completed;
  const navigate = useNavigate();

  const gradeClass: Record<string, string> = { A: "grade-a", B: "grade-b", C: "grade-c", D: "grade-d" };
  const gradeLabel: Record<string, string> = { A: "Strong evidence", B: "Good evidence", C: "Fair evidence", D: "Insufficient" };

  return (
    <div className="page-container wide">
      <div className="fade-up" style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: 0, marginBottom: 4 }}>
          {trial.conditionALabel} vs. {trial.conditionBLabel}
        </h1>
        <span style={{ fontSize: 13, color: "var(--gray-400)", fontFamily: "var(--mono)" }}>
          Completed {trial.completedAt ? new Date(trial.completedAt).toLocaleDateString() : ""} · {getTotalDaysLabel(trial)} · {trial.protocol.template ?? "Custom"}
        </span>
      </div>

      {/* Verdict */}
      <div className="verdict-card fade-up fade-up-1">
        <h2>{getVerdictHeadline(result, trial)}</h2>
        <p>{result.summary}</p>
        {result.meets_minimum_meaningful_effect === false && (
          <p>The measured difference is below the default threshold for a meaningful change.</p>
        )}
      </div>

      <div className="integrity-grid fade-up fade-up-2">
        <div className="integrity-item">
          <span>Evidence Basis</span>
          <strong className={evidenceClass[trial.ingestion.evidence_quality]}>
            {trial.ingestion.evidence_quality}
          </strong>
        </div>
        <div className="integrity-item">
          <span>Safety Tier</span>
          <strong className={safetyBadgeClass[trial.ingestion.safety_tier]}>
            {safetyLabel[trial.ingestion.safety_tier]}
          </strong>
        </div>
        <div className="integrity-item">
          <span>Adherence</span>
          <strong>{formatPct(result.adherence_rate)}</strong>
        </div>
        <div className="integrity-item">
          <span>Days Logged</span>
          <strong>{formatPct(result.days_logged_pct)}</strong>
        </div>
        <div className="integrity-item">
          <span>Early Stop</span>
          <strong>{result.early_stop ? "Yes" : "No"}</strong>
        </div>
        <div className="integrity-item">
          <span>Late Backfills Excluded</span>
          <strong>{result.late_backfill_excluded}</strong>
        </div>
      </div>

      <details className="advanced-disclosure fade-up fade-up-3">
        <summary>Statistics and chart</summary>
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">Mean A <InfoTooltip text={`Average daily score on days using ${trial.conditionALabel}.`} /></div>
            <div className="stat-value stat-positive">{result.mean_a?.toFixed(1) ?? "—"}</div>
            <div className="stat-sub">{trial.conditionALabel}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Mean B <InfoTooltip text={`Average daily score on days using ${trial.conditionBLabel}.`} /></div>
            <div className="stat-value">{result.mean_b?.toFixed(1) ?? "—"}</div>
            <div className="stat-sub">{trial.conditionBLabel}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Difference <InfoTooltip text="Mean A minus Mean B. The confidence interval tells you how certain this difference is." /></div>
            <div className="stat-value stat-positive">{result.difference != null ? `${result.difference > 0 ? "+" : ""}${result.difference.toFixed(1)}` : "—"}</div>
            <div className="stat-sub" style={{ fontFamily: "var(--mono)", fontSize: 11 }}>
              CI: [{result.ci_lower?.toFixed(1)}, {result.ci_upper?.toFixed(1)}]
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Quality <InfoTooltip text={`Grade ${result.quality_grade}: ${gradeLabel[result.quality_grade]}.`} /></div>
            <div className="stat-value">
              <span className={`grade-badge ${gradeClass[result.quality_grade]}`}>{result.quality_grade}</span>
            </div>
            <div className="stat-sub">{gradeLabel[result.quality_grade]}</div>
          </div>
        </div>

        <TimeSeriesChart
          observations={trial.observations}
          condALabel={trial.conditionALabel}
          condBLabel={trial.conditionBLabel}
        />
      </details>

      <details className="advanced-disclosure fade-up fade-up-4">
        <summary>Caveats</summary>
        <div className="caveats-card">
          <p><strong>Expectancy effect:</strong> This experiment was not blinded. You knew which product you were using, which can unconsciously influence your satisfaction ratings.</p>
          <p><strong>Regression to the mean:</strong> If you started the trial during a particularly good or bad skin period, some change may simply be a return to your baseline.</p>
          <p><strong>Personal evidence:</strong> This result applies to you, under these conditions, with this protocol. It is a useful record for conversations, not a diagnosis or care plan.</p>
          {result.caveats && <p>{result.caveats}</p>}
        </div>
      </details>

      {result.secondary_outcomes?.length ? (
        <details className="advanced-disclosure fade-up fade-up-4" open>
          <summary>Secondary outcomes</summary>
          <div className="advanced-grid">
            {result.secondary_outcomes.map((outcome) => (
              <div key={outcome.outcome_id}>
                <span>{outcome.label}</span>
                <strong>{outcome.difference != null ? signed(outcome.difference) : "—"}</strong>
                <small>A={outcome.mean_a?.toFixed(1) ?? "—"} · B={outcome.mean_b?.toFixed(1) ?? "—"}</small>
              </div>
            ))}
          </div>
          <ul className="advanced-list">
            {result.secondary_outcomes.map((outcome) => <li key={outcome.outcome_id}>{outcome.summary}</li>)}
          </ul>
        </details>
      ) : null}

      {(trial.adverseEvents?.length ?? 0) > 0 && (
        <details className="advanced-disclosure fade-up fade-up-4" open>
          <summary>Adverse event review</summary>
          <div className="caveats-card">
            <p>{result.adverse_event_count ?? trial.adverseEvents?.length ?? 0} discomfort log{(result.adverse_event_count ?? 0) === 1 ? "" : "s"} recorded.</p>
            <ul className="advanced-list">
              {trial.adverseEvents?.map((event) => (
                <li key={event.id}>
                  {event.date} · day {event.day_index} · {event.severity}: {event.description}
                </li>
              ))}
            </ul>
          </div>
        </details>
      )}

      <details className="advanced-disclosure fade-up fade-up-4" open>
        <summary>Appointment brief</summary>
        <div className="caveats-card">
          <p>
            A concise visit summary can help you remember what changed, what you tracked, and what
            you want to ask next.
          </p>
          {trial.ingestion.clinician_note || trial.protocol.clinician_note ? (
            <p>{trial.ingestion.clinician_note || trial.protocol.clinician_note}</p>
          ) : null}
          <h3 style={{ marginTop: 14 }}>Questions to bring</h3>
          <ul className="advanced-list">
            {doctorQuestions(trial, result).map((question) => <li key={question}>{question}</li>)}
          </ul>
          {(trial.adverseEvents?.length ?? 0) > 0 && (
            <>
              <h3 style={{ marginTop: 14 }}>Discomfort logged</h3>
              <ul className="advanced-list">
                {trial.adverseEvents?.map((event) => (
                  <li key={event.id}>
                    {event.date}: {event.severity} · {event.description}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </details>

      <details className="advanced-disclosure fade-up fade-up-4">
        <summary>Advanced analysis</summary>
        <div className="advanced-grid">
          <div>
            <span>Method</span>
            <strong>{result.analysis_method ?? "welch"}</strong>
          </div>
          <div>
            <span>Action</span>
            <strong>{formatActionability(result.actionability)}</strong>
          </div>
          <div>
            <span>Seed</span>
            <strong>{trial.seed}</strong>
          </div>
          <div>
            <span>Audit hash</span>
            <strong>{computeTrialAuditHash(trial)}</strong>
          </div>
          <div>
            <span>Protocol hash</span>
            <strong>{trial.protocolHash ?? "—"}</strong>
          </div>
          <div>
            <span>Analysis hash</span>
            <strong>{result.methods_appendix?.trial_lock?.analysis_plan_hash ?? trial.analysisPlanHash ?? "—"}</strong>
          </div>
          <div>
            <span>Meaningful threshold</span>
            <strong>{result.equivalence_margin ?? result.minimum_meaningful_difference ?? 0.5}</strong>
          </div>
          <div>
            <span>No meaningful difference</span>
            <strong>{result.supports_no_meaningful_difference == null ? "—" : result.supports_no_meaningful_difference ? "Supported" : "Not supported"}</strong>
          </div>
          <div>
            <span>Randomization p</span>
            <strong>{result.randomization_p_value?.toFixed(4) ?? "—"}</strong>
          </div>
          <div>
            <span>Rows used</span>
            <strong>{result.dataset_snapshot ? `${result.dataset_snapshot.rows_used_primary}/${result.dataset_snapshot.rows_total}` : "—"}</strong>
          </div>
          <div>
            <span>Cohen's d</span>
            <strong>{result.cohens_d?.toFixed(2) ?? "—"}</strong>
          </div>
        </div>
        {result.harm_benefit_summary && (
          <p className="advanced-copy">{result.harm_benefit_summary}</p>
        )}
        {result.paired_block?.difference != null && (
          <p className="advanced-copy">
            Paired-period estimate: {signed(result.paired_block.difference)} across {result.paired_block.n_pairs} pair{result.paired_block.n_pairs === 1 ? "" : "s"}.
          </p>
        )}
        {result.welch_sensitivity?.difference != null && (
          <p className="advanced-copy">
            Welch sensitivity: {signed(result.welch_sensitivity.difference)}.
          </p>
        )}
        {result.sensitivity_excluding_partial?.difference != null && (
          <p className="advanced-copy">
            Sensitivity without partial-adherence rows: {signed(result.sensitivity_excluding_partial.difference)}.
          </p>
        )}
        {result.reliability_warnings?.length ? (
          <ul className="advanced-list">{result.reliability_warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        ) : null}
        {result.data_warnings?.length ? (
          <ul className="advanced-list">{result.data_warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        ) : null}
        {result.block_breakdown.length > 0 && (
          <div className="block-table">
            {result.block_breakdown.map((block) => (
              <div key={`${block.block_index}-${block.condition}`}>
                <span>Period {block.block_index + 1} · {block.condition}</span>
                <strong>{block.mean.toFixed(1)}</strong>
                <small>n={block.n}</small>
              </div>
            ))}
          </div>
        )}
        <pre className="raw-json">{JSON.stringify({ trial, result }, null, 2)}</pre>
      </details>

      {/* Actions */}
      <div style={{ display: "flex", gap: 12, marginTop: 24 }} className="fade-up fade-up-5">
        <button className="btn btn-s" onClick={() => {
          downloadFile(exportCSV(trial.observations), "pitgpt-trial.csv", "text/csv");
        }}>
          Export CSV
        </button>
        <button className="btn btn-s" onClick={() => {
          downloadFile(JSON.stringify({ trial, result }, null, 2), "pitgpt-trial.json", "application/json");
        }}>
          Export JSON
        </button>
        <button className="btn btn-s" onClick={() => {
          downloadFile(JSON.stringify({ seed: trial.seed, schedule: trial.schedule }, null, 2), "pitgpt-schedule.json", "application/json");
        }}>
          Export Schedule
        </button>
        <button className="btn btn-s" onClick={() => {
          downloadFile(JSON.stringify(result.methods_appendix ?? {}, null, 2), "pitgpt-methods-appendix.json", "application/json");
        }}>
          Methods Appendix
        </button>
        <button className="btn btn-s" onClick={() => {
          downloadFile(exportAppointmentBrief(completed), "pitgpt-appointment-brief.md", "text/markdown");
        }}>
          Appointment Brief
        </button>
        <button className="btn btn-p" onClick={() => navigate("/")}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="5" stroke="#fff" strokeWidth="1.5" />
            <path d="M8 6v4M6 8h4" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          New Experiment
        </button>
      </div>
    </div>
  );
}

function getTotalDaysLabel(trial: CompletedTrial["trial"]): string {
  return `${trial.observations.length} days logged`;
}

function formatPct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function signed(value: number): string {
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}`;
}

function formatActionability(value: CompletedTrial["result"]["actionability"]): string {
  const labels: Record<string, string> = {
    switch: "Switch",
    keep_current: "Keep current",
    repeat_with_better_controls: "Repeat",
    stop_for_safety: "Stop for safety",
    inconclusive_no_action: "No change",
    insufficient_data: "Insufficient data",
  };
  return value ? labels[value] ?? value : "—";
}

function getVerdictHeadline(result: CompletedTrial["result"], trial: CompletedTrial["trial"]): string {
  if (result.verdict === "insufficient_data") return "Insufficient data for a conclusion.";
  if (result.verdict === "inconclusive") return "Results are inconclusive.";
  const winner = result.verdict === "favors_a" ? trial.conditionALabel : trial.conditionBLabel;
  if (result.difference == null) return `${winner} performed better in this trial.`;
  return `${winner} performed better by ${Math.abs(result.difference).toFixed(1)} points on average.`;
}

export function Results() {
  const { state } = useApp();
  const navigate = useNavigate();
  const [selectedIndex, setSelectedIndex] = useState(Math.max(0, state.completedResults.length - 1));

  const latest = state.completedResults[selectedIndex] ?? state.completedResults[state.completedResults.length - 1];

  if (!latest) {
    return (
      <div className="page-container" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh" }}>
        <div style={{ textAlign: "center" }}>
          <p style={{ color: "var(--gray-500)", marginBottom: 16 }}>No completed trials yet.</p>
          <button className="btn btn-p" onClick={() => navigate("/")}>Start a New Experiment</button>
        </div>
      </div>
    );
  }

  return (
    <>
      {state.completedResults.length > 1 && (
        <div className="page-container wide result-history">
          <h2>Result history</h2>
          <div className="history-list">
            {state.completedResults.map((completed, index) => (
              <button
                className={`history-item${index === selectedIndex ? " selected" : ""}`}
                key={completed.trial.id}
                onClick={() => setSelectedIndex(index)}
              >
                {completed.trial.conditionALabel} vs. {completed.trial.conditionBLabel}
                <span>{completed.result.quality_grade} · {completed.result.verdict}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      <ResultView completed={latest} />
    </>
  );
}

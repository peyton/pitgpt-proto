import { useNavigate } from "react-router-dom";
import { useApp } from "../lib/AppContext";
import { InfoTooltip } from "../components/InfoTooltip";
import { downloadFile, exportCSV } from "../lib/storage";
import type { CompletedTrial, Observation } from "../lib/types";

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
        <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-.5px", marginBottom: 4 }}>
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
      </div>

      {/* Stats Grid */}
      <div className="stats-grid fade-up fade-up-2">
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

      {/* Chart */}
      <TimeSeriesChart
        observations={trial.observations}
        condALabel={trial.conditionALabel}
        condBLabel={trial.conditionBLabel}
      />

      {/* Caveats */}
      <div className="caveats-card fade-up fade-up-4">
        <h3>
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
            <path d="M10 2l8 14H2L10 2z" stroke="var(--caution)" strokeWidth="1.5" strokeLinejoin="round" fill="var(--caution-bg)" />
            <path d="M10 8v3M10 13v1" stroke="var(--caution)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          Important Caveats
        </h3>
        <p><strong>Expectancy effect:</strong> This experiment was not blinded. You knew which product you were using, which can unconsciously influence your satisfaction ratings.</p>
        <p><strong>Regression to the mean:</strong> If you started the trial during a particularly good or bad skin period, some "change" may simply be a return to your baseline.</p>
        <p><strong>Personal evidence only:</strong> This result applies to you, under these conditions, with this protocol. It is not generalizable and does not constitute medical advice.</p>
        {result.caveats && <p>{result.caveats}</p>}
      </div>

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

function getVerdictHeadline(result: CompletedTrial["result"], trial: CompletedTrial["trial"]): string {
  if (result.verdict === "insufficient_data") return "Insufficient data for a conclusion.";
  if (result.verdict === "inconclusive") return "Results are inconclusive.";
  const winner = result.verdict === "favors_a" ? trial.conditionALabel : trial.conditionBLabel;
  const pct = result.mean_a != null && result.mean_b != null
    ? Math.round((Math.max(result.n_used_a, result.n_used_b) / (result.n_used_a + result.n_used_b)) * 100)
    : null;
  return pct ? `${winner} scored higher on ${pct}% of days.` : `${winner} performed better in this trial.`;
}

export function Results() {
  const { state } = useApp();
  const navigate = useNavigate();

  const latest = state.completedResults[state.completedResults.length - 1];

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

  return <ResultView completed={latest} />;
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../lib/AppContext";
import { getSafetyBadgeClass, getSafetyLabel, getEvidenceClass } from "../lib/badges";
import { createTrial } from "../lib/trial";
import { InfoTooltip } from "../components/InfoTooltip";
import { getPeriodCount } from "../lib/randomize";
import { trialTemplates } from "../lib/templates";

export function ProtocolReview() {
  const { ingestionResult, protocolExperimentId, setTrial, linkExperimentTrial } = useApp();
  const navigate = useNavigate();
  const [condA, setCondA] = useState("");
  const [condB, setCondB] = useState("");
  const [restrictedAcknowledged, setRestrictedAcknowledged] = useState(false);

  if (!ingestionResult) {
    return (
      <div className="page-container empty-state-center">
        <div className="empty-state">
          <p>No protocol generated yet.</p>
          <button className="btn btn-p" onClick={() => navigate("/")}>Start a New Experiment</button>
        </div>
      </div>
    );
  }

  const {
    decision,
    safety_tier,
    evidence_quality,
    protocol,
    block_reason,
    user_message,
    risk_level,
    risk_rationale,
    clinician_note,
  } = ingestionResult;

  if (decision === "block") {
    return (
      <div className="page-container">
        <div className="page-header fade-up">
          <button className="back-link" type="button" onClick={() => navigate("/")}>
            ← Back
          </button>
          <h1 className="page-title">Experiment Blocked</h1>
          <span className={getSafetyBadgeClass(safety_tier)}>
            {getSafetyLabel(safety_tier)}
          </span>
        </div>
        <div className="caveats-card fade-up fade-up-1">
          <h3>Why this was blocked</h3>
          <p>{block_reason}</p>
          {user_message && <p className="user-message">{user_message}</p>}
        </div>
        <div className="page-actions-start">
          <button className="btn btn-p" onClick={() => navigate("/")}>Try a Different Question</button>
        </div>
      </div>
    );
  }

  if (decision === "manual_review_before_protocol") {
    return (
      <div className="page-container">
        <div className="page-header fade-up">
          <button className="back-link" type="button" onClick={() => navigate("/")}>
            ← Back
          </button>
          <h1 className="page-title">Manual Review Needed</h1>
          <span className={getSafetyBadgeClass(safety_tier)}>
            {getSafetyLabel(safety_tier)}
          </span>
        </div>
        <div className="caveats-card fade-up fade-up-1">
          <h3>Protocol not ready to lock</h3>
          <p>{user_message}</p>
          {block_reason && <p>{block_reason}</p>}
          {ingestionResult.next_steps && ingestionResult.next_steps.length > 0 && (
            <>
              <h3>Follow-up questions</h3>
              <ul>
                {ingestionResult.next_steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
            </>
          )}
          <p>
            Try narrowing the comparison to two everyday routines or products with a single 0-10 outcome.
          </p>
        </div>
        <div className="page-actions-start">
          <button className="btn btn-p" onClick={() => navigate("/")}>Revise Question</button>
        </div>
      </div>
    );
  }

  if (!protocol) {
    return (
      <div className="page-container">
        <p className="page-subtitle">{user_message || "No protocol was generated."}</p>
        <button className="btn btn-p" onClick={() => navigate("/")}>Try Again</button>
      </div>
    );
  }

  const totalDays = protocol.duration_weeks * 7;
  const totalPeriods = getPeriodCount(protocol.duration_weeks, protocol.block_length_days);
  const templateHints = trialTemplates.find((template) => template.protocol.template === protocol.template);
  const requiresAcknowledgment =
    decision === "generate_protocol_with_restrictions" || safety_tier === "YELLOW";

  const handleLock = () => {
    if (requiresAcknowledgment && !restrictedAcknowledged) return;
    const labelA = condA.trim() || protocol.condition_a_label?.trim() || "Condition A";
    const labelB = condB.trim() || protocol.condition_b_label?.trim() || "Condition B";
    const trial = createTrial(ingestionResult, labelA, labelB);
    setTrial(trial);
    if (protocolExperimentId) {
      linkExperimentTrial(protocolExperimentId, trial.id);
    }
    navigate("/trial");
  };

  return (
    <div className="page-container">
      <div className="page-header fade-up">
        <button className="back-link" type="button" onClick={() => navigate("/")}>
          ← Back
        </button>
        <h1 className="page-title">Generated Protocol</h1>
        <p className="page-subtitle">
          Edit condition labels, then lock the protocol to start collecting data.
        </p>
      </div>

      <div className="badge-row fade-up fade-up-1">
        <span className={getSafetyBadgeClass(safety_tier)}>
          {getSafetyLabel(safety_tier)}
        </span>
        <span className={getEvidenceClass(evidence_quality)}>
          {evidence_quality} Evidence
        </span>
        {risk_level && <span className="badge badge-info">{risk_level.replaceAll("_", " ")}</span>}
        {protocol.template && <span className="badge badge-neutral">{protocol.template}</span>}
      </div>

      {(risk_rationale || clinician_note || protocol.clinician_note) && (
        <div className="caveats-card fade-up fade-up-1" style={{ marginBottom: 20 }}>
          <h3>Risk review</h3>
          {risk_rationale && <p>{risk_rationale}</p>}
          {(clinician_note || protocol.clinician_note) && (
            <p>{clinician_note || protocol.clinician_note}</p>
          )}
        </div>
      )}

      {/* Conditions */}
      <div className="protocol-card fade-up fade-up-2">
        <div className="protocol-card-header">
          <h3>You can edit this</h3>
          <InfoTooltip text="The two routines or products you're comparing. Each will be randomly assigned to different periods." />
        </div>
        <div className="protocol-card-body">
          <div className="protocol-detail">
            <div className="protocol-detail-item">
              <label>Condition A</label>
              <div className="condition-input-row">
                <span className="condition-dot condition-dot-a" aria-hidden="true" />
                <input
                  type="text"
                  className="condition-input"
                  value={condA}
                  onChange={(e) => setCondA(e.target.value)}
                  placeholder={templateHints?.conditionAPlaceholder ?? "e.g. CeraVe Moisturizing Cream"}
                />
              </div>
            </div>
            <div className="protocol-detail-item">
              <label>Condition B</label>
              <div className="condition-input-row">
                <span className="condition-dot condition-dot-b" aria-hidden="true" />
                <input
                  type="text"
                  className="condition-input"
                  value={condB}
                  onChange={(e) => setCondB(e.target.value)}
                  placeholder={templateHints?.conditionBPlaceholder ?? "e.g. La Roche-Posay Toleriane"}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Design Parameters */}
      <div className="protocol-card fade-up fade-up-3">
        <div className="protocol-card-header">
          <h3>Locked for validity</h3>
          <span className="locked-badge">LOCKED</span>
        </div>
        <div className="protocol-card-body">
          <div className="protocol-detail">
            <div className="protocol-detail-item">
              <label>Primary Outcome <InfoTooltip text="The single measurement that determines which condition wins. Locked to prevent unconscious bias from changing goals mid-trial." /></label>
              <div className="value">{protocol.primary_outcome_question || "Satisfaction (0–10)"}</div>
            </div>
            {(protocol.outcome_anchor_low || protocol.outcome_anchor_mid || protocol.outcome_anchor_high) && (
              <div className="protocol-detail-item">
                <label>Outcome Anchors</label>
                <div className="value" style={{ fontSize: 14, lineHeight: 1.5 }}>
                  {[protocol.outcome_anchor_low, protocol.outcome_anchor_mid, protocol.outcome_anchor_high].filter(Boolean).join(" · ")}
                </div>
              </div>
            )}
            <div className="protocol-detail-item">
              <label>Duration</label>
              <div className="value">{protocol.duration_weeks} weeks ({totalDays} days)</div>
            </div>
            <div className="protocol-detail-item">
              <label>Block Length <InfoTooltip text="Each pair has one A period and one B period in random order. This controls for time trends." /></label>
              <div className="value">{protocol.block_length_days}-day periods ({Math.ceil(totalPeriods / 2)} pair{Math.ceil(totalPeriods / 2) === 1 ? "" : "s"})</div>
            </div>
            <div className="protocol-detail-item">
              <label>Check-in Cadence</label>
              <div className="value" style={{ textTransform: "capitalize" }}>{protocol.cadence}</div>
            </div>
            <div className="protocol-detail-item">
              <label>Washout <InfoTooltip text="A gap between conditions to let the previous product's effects fade." /></label>
              <div className="value">{protocol.washout || "None required"}</div>
            </div>
            <div className="protocol-detail-item">
              <label>Analysis Method</label>
              <div className="value mono">paired periods + Welch sensitivity</div>
            </div>
            <div className="protocol-detail-item">
              <label>Random Seed</label>
              <div className="value mono">generated when locked</div>
            </div>
            {protocol.suggested_confounders?.length ? (
              <div className="protocol-detail-item">
                <label>Optional Context To Note</label>
                <div className="value" style={{ fontSize: 14 }}>
                  {protocol.suggested_confounders.join(", ")}
                </div>
              </div>
            ) : null}
          </div>

          <div className="schedule-section">
            <label className="schedule-label">
              Randomized Periods <InfoTooltip text="You only see the current assignment while the trial is active. Future assignments are hidden to prevent bias." />
            </label>
            <div className="schedule-vis">
              {Array.from({ length: totalPeriods }, (_, i) => (
                <div key={i} className="schedule-block schedule-hidden">
                  P{i + 1}: days {i * protocol.block_length_days + 1}-{Math.min(totalDays, (i + 1) * protocol.block_length_days)}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {(ingestionResult.source_summaries?.length || ingestionResult.claimed_outcomes?.length) ? (
        <details className="advanced-disclosure fade-up fade-up-4">
          <summary>Research notes used</summary>
          {ingestionResult.source_summaries?.length ? (
            <>
              <h4>Source summaries</h4>
              <ul>{ingestionResult.source_summaries.map((item) => <li key={item}>{item}</li>)}</ul>
            </>
          ) : null}
          {ingestionResult.claimed_outcomes?.length ? (
            <>
              <h4>Claimed outcomes</h4>
              <ul>{ingestionResult.claimed_outcomes.map((item) => <li key={item}>{item}</li>)}</ul>
            </>
          ) : null}
        </details>
      ) : null}

      {/* Caveats */}
      <div className="caveats-box fade-up fade-up-4">
        <h4>Before you start</h4>
        <ul>
          <li>This experiment is not blinded — you'll know which product you're using, which can influence ratings.</li>
          <li>Results reflect your personal experience under this specific protocol, not a diagnosis or care plan.</li>
          <li>Once locked, the primary outcome and analysis method cannot be changed.</li>
          {protocol.warnings && <li>{protocol.warnings}</li>}
        </ul>
      </div>

      {decision === "generate_protocol_with_restrictions" && protocol.screening && (
        <div className="screening-banner">
          <strong>Screening:</strong> {protocol.screening}
        </div>
      )}

      {requiresAcknowledgment && (
        <label className="acknowledgment-box fade-up fade-up-5">
          <input
            type="checkbox"
            checked={restrictedAcknowledged}
            onChange={(e) => setRestrictedAcknowledged(e.target.checked)}
          />
          <span>
            I reviewed the restrictions and can keep this routine consistent without changing medications or replacing care.
          </span>
        </label>
      )}

      {user_message && <p className="user-message">{user_message}</p>}

      <div className="page-actions fade-up fade-up-5">
        <button className="btn btn-s" onClick={() => navigate("/")}>Start Over</button>
        <button className="btn btn-p" onClick={handleLock} disabled={requiresAcknowledgment && !restrictedAcknowledged}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 8h12M10 4l4 4-4 4" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Lock Protocol &amp; Start
        </button>
      </div>
    </div>
  );
}

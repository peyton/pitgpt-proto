import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../lib/AppContext";
import { createTrial } from "../lib/trial";
import { InfoTooltip } from "../components/InfoTooltip";

const safetyBadgeClass: Record<string, string> = {
  GREEN: "badge badge-safe badge-dot",
  YELLOW: "badge badge-caution badge-dot",
  RED: "badge badge-danger badge-dot",
};

const safetyLabel: Record<string, string> = {
  GREEN: "Green — Safe to Run",
  YELLOW: "Yellow — Review Carefully",
  RED: "Red — Not Recommended",
};

const evidenceClass: Record<string, string> = {
  strong: "badge badge-safe",
  moderate: "badge badge-info",
  weak: "badge badge-neutral",
  novel: "badge badge-pink",
};

export function ProtocolReview() {
  const { ingestionResult, setTrial } = useApp();
  const navigate = useNavigate();
  const [condA, setCondA] = useState("");
  const [condB, setCondB] = useState("");
  const [restrictedAcknowledged, setRestrictedAcknowledged] = useState(false);

  if (!ingestionResult) {
    return (
      <div className="page-container" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh" }}>
        <div style={{ textAlign: "center" }}>
          <p style={{ color: "var(--gray-500)", marginBottom: 16 }}>No protocol generated yet.</p>
          <button className="btn btn-p" onClick={() => navigate("/")}>Start a New Experiment</button>
        </div>
      </div>
    );
  }

  const { decision, safety_tier, evidence_quality, protocol, block_reason, user_message } = ingestionResult;

  if (decision === "block") {
    return (
      <div className="page-container">
        <div className="fade-up" style={{ marginBottom: 32 }}>
          <div className="back-link" onClick={() => navigate("/")} style={{ fontSize: 13, color: "var(--gray-400)", display: "flex", alignItems: "center", gap: 6, marginBottom: 16, cursor: "pointer" }}>
            ← Back to new experiment
          </div>
          <h1 style={{ fontSize: 30, fontWeight: 800, marginBottom: 8 }}>Experiment Blocked</h1>
          <span className={safetyBadgeClass[safety_tier]}>{safetyLabel[safety_tier]}</span>
        </div>
        <div className="caveats-card fade-up fade-up-1">
          <h3>Why this was blocked</h3>
          <p>{block_reason}</p>
          <p style={{ marginTop: 12 }}>{user_message}</p>
        </div>
        <div style={{ marginTop: 24 }}>
          <button className="btn btn-p" onClick={() => navigate("/")}>Try a Different Question</button>
        </div>
      </div>
    );
  }

  if (decision === "manual_review_before_protocol") {
    return (
      <div className="page-container">
        <div className="fade-up" style={{ marginBottom: 32 }}>
          <div
            className="back-link"
            onClick={() => navigate("/")}
            style={{ fontSize: 13, color: "var(--gray-400)", display: "flex", alignItems: "center", gap: 6, marginBottom: 16, cursor: "pointer" }}
          >
            ← Back to new experiment
          </div>
          <h1 style={{ fontSize: 30, fontWeight: 800, marginBottom: 8 }}>Manual Review Needed</h1>
          <span className={safetyBadgeClass[safety_tier]}>{safetyLabel[safety_tier]}</span>
        </div>
        <div className="caveats-card fade-up fade-up-1">
          <h3>Protocol not ready to lock</h3>
          <p>{user_message}</p>
          {block_reason && <p style={{ marginTop: 12 }}>{block_reason}</p>}
          <p style={{ marginTop: 12 }}>
            Try narrowing the comparison to two everyday routines or products with a single 0-10 outcome.
          </p>
        </div>
        <div style={{ marginTop: 24 }}>
          <button className="btn btn-p" onClick={() => navigate("/")}>Revise Question</button>
        </div>
      </div>
    );
  }

  if (!protocol) {
    return (
      <div className="page-container">
        <p style={{ color: "var(--gray-500)" }}>No protocol was generated. {user_message}</p>
        <button className="btn btn-p" style={{ marginTop: 16 }} onClick={() => navigate("/")}>Try Again</button>
      </div>
    );
  }

  const totalWeeks = protocol.duration_weeks;
  const requiresAcknowledgment =
    decision === "generate_protocol_with_restrictions" || safety_tier === "YELLOW";

  const handleLock = () => {
    if (requiresAcknowledgment && !restrictedAcknowledged) return;
    const labelA = condA.trim() || "Condition A";
    const labelB = condB.trim() || "Condition B";
    const trial = createTrial(ingestionResult, labelA, labelB);
    setTrial(trial);
    navigate("/trial");
  };

  return (
    <div className="page-container">
      <div className="fade-up" style={{ marginBottom: 32 }}>
        <div
          onClick={() => navigate("/")}
          style={{ fontSize: 13, color: "var(--gray-400)", display: "flex", alignItems: "center", gap: 6, marginBottom: 16, cursor: "pointer" }}
        >
          ← Back to new experiment
        </div>
        <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-.5px", marginBottom: 8 }}>Generated Protocol</h1>
        <p style={{ color: "var(--gray-500)", fontSize: 15 }}>
          Review the experiment design below. You can edit condition labels, but the scientific parameters are locked for validity.
        </p>
      </div>

      <div className="fade-up fade-up-1" style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        <span className={safetyBadgeClass[safety_tier]}>{safetyLabel[safety_tier]}</span>
        <span className={evidenceClass[evidence_quality]}>{evidence_quality} Evidence</span>
        {protocol.template && <span className="badge badge-neutral">{protocol.template}</span>}
      </div>

      {/* Conditions */}
      <div className="protocol-card fade-up fade-up-2">
        <div className="protocol-card-header">
          <h3>Conditions</h3>
          <InfoTooltip text="The two routines or products you're comparing. Each will be randomly assigned to different weeks." />
        </div>
        <div className="protocol-card-body">
          <div className="protocol-detail">
            <div className="protocol-detail-item">
              <label>Condition A</label>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 12, height: 12, borderRadius: "50%", background: "var(--pink-500)", flexShrink: 0 }} />
                <input
                  type="text"
                  value={condA}
                  onChange={(e) => setCondA(e.target.value)}
                  placeholder="e.g. CeraVe Moisturizing Cream"
                  style={{ border: "1px solid var(--gray-200)", borderRadius: "var(--r-md)", padding: "8px 12px", fontSize: 15, fontWeight: 600, width: "100%", outline: "none", fontFamily: "var(--font)" }}
                />
              </div>
            </div>
            <div className="protocol-detail-item">
              <label>Condition B</label>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 12, height: 12, borderRadius: "50%", background: "var(--pink-300)", flexShrink: 0 }} />
                <input
                  type="text"
                  value={condB}
                  onChange={(e) => setCondB(e.target.value)}
                  placeholder="e.g. La Roche-Posay Toleriane"
                  style={{ border: "1px solid var(--gray-200)", borderRadius: "var(--r-md)", padding: "8px 12px", fontSize: 15, fontWeight: 600, width: "100%", outline: "none", fontFamily: "var(--font)" }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Design Parameters */}
      <div className="protocol-card fade-up fade-up-3">
        <div className="protocol-card-header">
          <h3>Design Parameters</h3>
          <span style={{ fontSize: 11, color: "var(--gray-400)", fontFamily: "var(--mono)" }}>LOCKED</span>
        </div>
        <div className="protocol-card-body">
          <div className="protocol-detail">
            <div className="protocol-detail-item">
              <label>Primary Outcome <InfoTooltip text="The single measurement that determines which condition wins. Locked to prevent unconscious bias from changing goals mid-trial." /></label>
              <div className="value">{protocol.primary_outcome_question || "Satisfaction (0–10)"}</div>
            </div>
            <div className="protocol-detail-item">
              <label>Duration</label>
              <div className="value">{protocol.duration_weeks} weeks ({protocol.duration_weeks * 7} days)</div>
            </div>
            <div className="protocol-detail-item">
              <label>Block Length <InfoTooltip text="Each 'block' is a pair of weeks — one assigned to A and one to B, in random order. This controls for time trends." /></label>
              <div className="value">{protocol.block_length_days}-day blocks ({Math.floor(totalWeeks / 2)} pairs)</div>
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
              <div className="value mono">Welch's t-test + 95% CI</div>
            </div>
          </div>

          <div style={{ marginTop: 20 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: ".04em", color: "var(--gray-400)", marginBottom: 10 }}>
              Randomized Schedule <InfoTooltip text="You only see the current week's assignment. Future assignments are hidden to prevent bias." />
            </label>
            <div className="schedule-vis">
              {Array.from({ length: totalWeeks }, (_, i) => (
                <div key={i} className="schedule-block schedule-hidden">Wk {i + 1}: ?</div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Caveats */}
      <div className="caveats-box fade-up fade-up-4">
        <h4>Before you start</h4>
        <ul>
          <li>This experiment is not blinded — you'll know which product you're using, which can influence ratings.</li>
          <li>Results reflect your personal experience under this specific protocol, not a general medical claim.</li>
          <li>Once locked, the primary outcome and analysis method cannot be changed.</li>
          {protocol.warnings && <li>{protocol.warnings}</li>}
        </ul>
      </div>

      {decision === "generate_protocol_with_restrictions" && protocol.screening && (
        <div style={{ background: "var(--caution-bg)", border: "1px solid #FDE68A", borderRadius: "var(--r-md)", padding: "14px 20px", fontSize: 13, color: "var(--caution)", marginTop: 16 }}>
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
            I reviewed the restrictions and will only compare routines or products that fit this protocol.
          </span>
        </label>
      )}

      <p style={{ fontSize: 14, color: "var(--gray-500)", marginTop: 16 }}>{user_message}</p>

      <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", marginTop: 24, paddingTop: 24, borderTop: "1px solid var(--gray-200)" }} className="fade-up fade-up-5">
        <button className="btn btn-s" onClick={() => navigate("/")}>Edit Conditions</button>
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

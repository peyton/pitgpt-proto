import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../lib/AppContext";
import { ingest } from "../lib/api";

const templates = [
  { icon: "🧴", name: "Skincare A/B", desc: "Compare two products over 6 weeks", query: "Compare two skincare products" },
  { icon: "🌅", name: "Morning Routine", desc: "Test which routine works better", query: "Compare two morning routines" },
  { icon: "💤", name: "Sleep Routine", desc: "Compare sleep habits over 4 weeks", query: "Compare two sleep routines" },
  { icon: "💇", name: "Haircare", desc: "Which product gives better results?", query: "Compare two haircare products" },
  { icon: "🌙", name: "Evening Routine", desc: "A/B test your night routine", query: "Compare two evening routines" },
  { icon: "⚗️", name: "Custom A/B", desc: "Design your own experiment", query: "Custom A/B experiment" },
];

const quickPrompts = [
  '"Does retinol actually help?"',
  '"Vitamin C serum vs niacinamide"',
  '"Is my morning routine worth it?"',
];

export function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { setIngestionResult, state } = useApp();

  const handleSubmit = useCallback(
    async (q: string) => {
      const trimmed = q.trim();
      if (!trimmed) return;
      setLoading(true);
      setError(null);
      try {
        const result = await ingest(trimmed);
        setIngestionResult(result);
        navigate("/protocol");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Something went wrong");
      } finally {
        setLoading(false);
      }
    },
    [navigate, setIngestionResult],
  );

  const handleFileUpload = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        const text = reader.result as string;
        setQuery(text.slice(0, 2000));
      };
      reader.readAsText(file);
    },
    [],
  );

  const autoResize = (el: HTMLTextAreaElement) => {
    el.style.height = "auto";
    el.style.height = el.scrollHeight + "px";
  };

  // If there's an active trial, show a link to it
  if (state.trial?.status === "active") {
    return (
      <div className="home-center">
        <div className="fade-up" style={{ textAlign: "center" }}>
          <h1 style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-1.5px", marginBottom: 12 }}>
            Trial in Progress
          </h1>
          <p style={{ color: "var(--gray-500)", fontSize: 16, maxWidth: 460, margin: "0 auto 32px" }}>
            You have an active trial: <strong>{state.trial.conditionALabel} vs. {state.trial.conditionBLabel}</strong>
          </p>
          <button className="btn btn-p" onClick={() => navigate("/trial")}>
            Go to Active Trial
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="home-center">
      <div className="fade-up" style={{ textAlign: "center", marginBottom: 40 }}>
        <h1 style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-1.5px", marginBottom: 12, lineHeight: 1.1 }}>
          What do you want to test?
        </h1>
        <p style={{ color: "var(--gray-500)", fontSize: 16, maxWidth: 460, margin: "0 auto" }}>
          Ask a question, paste a link, or upload a study — and get a structured personal experiment in minutes.
        </p>
      </div>

      <div className="fade-up fade-up-1" style={{ width: "100%", maxWidth: 620, marginBottom: 32 }}>
        <div className="chat-input">
          <textarea
            ref={textareaRef}
            rows={1}
            placeholder='"Is CeraVe or La Roche-Posay better for my dry skin?"'
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              autoResize(e.target);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(query);
              }
            }}
            disabled={loading}
          />
          <div className="chat-actions">
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.pdf,.md"
              style={{ display: "none" }}
              onChange={handleFileUpload}
            />
            <button
              className="chat-action-btn"
              aria-label="Upload file"
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
            >
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                <path d="M10 2v12M6 6l4-4 4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M3 14v2a2 2 0 002 2h10a2 2 0 002-2v-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
            <button
              className="chat-send"
              aria-label="Generate protocol"
              onClick={() => handleSubmit(query)}
              disabled={loading}
            >
              {loading ? (
                <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
              ) : (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M2 8h12M10 4l4 4-4 4" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </button>
          </div>
        </div>
        {error && (
          <p style={{ color: "var(--danger)", fontSize: 13, marginTop: 8, textAlign: "center" }}>{error}</p>
        )}
      </div>

      <div className="fade-up fade-up-2" style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: ".08em", color: "var(--gray-400)", marginBottom: 12, textAlign: "center" }}>
        Or start from a template
      </div>
      <div className="template-grid fade-up fade-up-3">
        {templates.map((t) => (
          <div key={t.name} className="template-card" onClick={() => { setQuery(t.query); handleSubmit(t.query); }}>
            <div className="template-icon">{t.icon}</div>
            <h3>{t.name}</h3>
            <p>{t.desc}</p>
          </div>
        ))}
      </div>
      <div className="fade-up fade-up-4" style={{ display: "flex", gap: 8, flexWrap: "wrap" as const, justifyContent: "center", marginTop: 24, maxWidth: 620 }}>
        {quickPrompts.map((prompt) => (
          <button
            key={prompt}
            className="radio-pill"
            style={{ fontSize: 13 }}
            onClick={() => { setQuery(prompt); handleSubmit(prompt); }}
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

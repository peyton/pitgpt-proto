import { useCallback, useRef, useState, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../lib/AppContext";
import { ingest } from "../lib/api";
import {
  templateToIngestionResult,
  trialTemplates,
  type TrialTemplate,
} from "../lib/templates";

interface SourceDocument {
  id: string;
  name: string;
  content: string;
}

const quickPrompts = [
  '"CeraVe vs La Roche-Posay for dry skin"',
  '"Vitamin C serum vs niacinamide"',
  '"Current morning routine vs simpler routine"',
];

function sourceId(): string {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

export function Home() {
  const [query, setQuery] = useState("");
  const [sourceText, setSourceText] = useState("");
  const [sources, setSources] = useState<SourceDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { setIngestionResult, state } = useApp();

  const addSource = useCallback((name: string, content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;
    setSources((current) => [
      ...current,
      { id: sourceId(), name, content: trimmed.slice(0, 12000) },
    ]);
  }, []);

  const handleSubmit = useCallback(
    async (q: string) => {
      const trimmed = q.trim();
      if (!trimmed) {
        setError("Add a question to frame the experiment.");
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const result = await ingest(
          trimmed,
          sources.map((source) => source.content),
        );
        setIngestionResult(result);
        navigate("/protocol");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not generate a protocol.");
      } finally {
        setLoading(false);
      }
    },
    [navigate, setIngestionResult, sources],
  );

  const handleFileUpload = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        addSource(file.name, String(reader.result ?? ""));
        event.target.value = "";
      };
      reader.onerror = () => setError("Could not read that source file.");
      reader.readAsText(file);
    },
    [addSource],
  );

  const handleAddPastedSource = useCallback(() => {
    addSource("Pasted source", sourceText);
    setSourceText("");
  }, [addSource, sourceText]);

  const handleTemplateStart = useCallback(
    (template: TrialTemplate) => {
      setError(null);
      setIngestionResult(templateToIngestionResult(template));
      navigate("/protocol");
    },
    [navigate, setIngestionResult],
  );

  const autoResize = (el: HTMLTextAreaElement) => {
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  };

  if (state.trial?.status === "active") {
    return (
      <div className="home-center">
        <div className="fade-up" style={{ textAlign: "center" }}>
          <h1 style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-1.5px", marginBottom: 12 }}>
            Trial in Progress
          </h1>
          <p style={{ color: "var(--gray-500)", fontSize: 16, maxWidth: 460, margin: "0 auto 32px" }}>
            Active trial: <strong>{state.trial.conditionALabel} vs. {state.trial.conditionBLabel}</strong>
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
      <div className="fade-up" style={{ textAlign: "center", marginBottom: 32 }}>
        <h1 style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-1.5px", marginBottom: 12, lineHeight: 1.1 }}>
          What do you want to test?
        </h1>
        <p style={{ color: "var(--gray-500)", fontSize: 16, maxWidth: 500, margin: "0 auto" }}>
          Ask a question, add source material, or start from a locked template.
        </p>
      </div>

      <div className="fade-up fade-up-1" style={{ width: "100%", maxWidth: 680, marginBottom: 24 }}>
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
            aria-label="Experiment question"
          />
          <div className="chat-actions">
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,.pdf"
              style={{ display: "none" }}
              onChange={handleFileUpload}
            />
            <button
              className="chat-action-btn"
              aria-label="Upload source file"
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
          <p className="form-error" role="alert">{error}</p>
        )}
      </div>

      <div className="source-panel fade-up fade-up-2">
        <div className="source-panel-header">
          <div>
            <h2>Source Material</h2>
            <p>Paste abstracts, notes, claims, or product details. Sources stay separate from your question.</p>
          </div>
          <button
            className="btn btn-s btn-sm"
            onClick={handleAddPastedSource}
            disabled={!sourceText.trim() || loading}
          >
            Add Source
          </button>
        </div>
        <textarea
          className="source-textarea"
          placeholder="Paste source text here..."
          value={sourceText}
          onChange={(e) => setSourceText(e.target.value)}
          disabled={loading}
          aria-label="Source material"
        />
        {sources.length > 0 && (
          <div className="source-list" aria-label="Attached sources">
            {sources.map((source) => (
              <div className="source-chip" key={source.id}>
                <span>{source.name}</span>
                <small>{source.content.length.toLocaleString()} chars</small>
                <button
                  type="button"
                  aria-label={`Remove ${source.name}`}
                  onClick={() => setSources((current) => current.filter((item) => item.id !== source.id))}
                  disabled={loading}
                >
                  x
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="fade-up fade-up-3" style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center", marginTop: 20, maxWidth: 680 }}>
        {quickPrompts.map((prompt) => (
          <button
            key={prompt}
            className="radio-pill"
            style={{ fontSize: 13 }}
            onClick={() => {
              setQuery(prompt.replaceAll('"', ""));
              textareaRef.current?.focus();
            }}
          >
            {prompt}
          </button>
        ))}
      </div>

      <div className="fade-up fade-up-4" style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--gray-400)", marginTop: 30, marginBottom: 12, textAlign: "center" }}>
        Or start from a local template
      </div>
      <div className="template-grid fade-up fade-up-5">
        {trialTemplates.map((template) => (
          <button
            key={template.id}
            type="button"
            className="template-card"
            onClick={() => handleTemplateStart(template)}
          >
            <div className="template-icon">{template.icon}</div>
            <h3>{template.name}</h3>
            <p>{template.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

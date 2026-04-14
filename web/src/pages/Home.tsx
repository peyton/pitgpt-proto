import { useCallback, useEffect, useRef, useState, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../lib/AppContext";
import { analyzeExample, ingest } from "../lib/api";
import { isTauriRuntime } from "../lib/runtime";
import {
  createExampleCompletedTrial,
  templateToIngestionResult,
  trialTemplates,
  type TrialTemplate,
} from "../lib/templates";
import type { AiProviderKind, IngestionResult } from "../lib/types";

interface SourceDocument {
  id: string;
  name: string;
  content: string;
}

const MAX_SOURCE_CHARS = 12_000;
const MAX_TOTAL_SOURCE_CHARS = 40_000;

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
  const [sourceOpen, setSourceOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingExample, setLoadingExample] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const activeIngestRef = useRef<{ id: number; controller: AbortController } | null>(null);
  const requestIdRef = useRef(0);
  const navigate = useNavigate();
  const { completeTrial, setIngestionResult, state } = useApp();

  useEffect(() => {
    return () => {
      activeIngestRef.current?.controller.abort();
      activeIngestRef.current = null;
    };
  }, []);

  const addSource = useCallback((name: string, content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;
    if (trimmed.length > MAX_SOURCE_CHARS) {
      setError("That source is too large. Keep each source under 12,000 characters.");
      return;
    }
    if (sources.some((source) => source.content === trimmed)) {
      setError("That source is already attached.");
      return;
    }
    const totalChars = sources.reduce((total, source) => total + source.content.length, 0);
    if (totalChars + trimmed.length > MAX_TOTAL_SOURCE_CHARS) {
      setError("Attached sources are too large in total. Keep all sources under 40,000 characters.");
      return;
    }
    setSourceOpen(true);
    setError(null);
    setSources((current) => [
      ...current,
      { id: sourceId(), name, content: trimmed },
    ]);
  }, [sources]);

  const handleSubmit = useCallback(
    async (q: string) => {
      const trimmed = q.trim();
      if (!trimmed) {
        setError("Add a question to frame the experiment.");
        return;
      }
      if (activeIngestRef.current) return;
      const controller = new AbortController();
      const requestId = requestIdRef.current + 1;
      requestIdRef.current = requestId;
      activeIngestRef.current = { id: requestId, controller };
      setLoading(true);
      setError(null);
      try {
        const result = await ingest(
          trimmed,
          sources.map((source) => source.content),
          state.settings.preferredModel || undefined,
          getProviderForRuntime(state.settings.preferredProvider),
          { signal: controller.signal },
        );
        if (controller.signal.aborted || activeIngestRef.current?.id !== requestId) return;
        setIngestionResult(enrichIngestionResult(result, sources));
        navigate("/protocol");
      } catch (e) {
        if (isAbortError(e) || controller.signal.aborted || activeIngestRef.current?.id !== requestId) {
          return;
        }
        const message = e instanceof Error ? e.message : "Could not generate a protocol.";
        setError(
          message.includes("OPENROUTER_API_KEY")
            ? "Protocol generation needs an API key. You can still run the example or start from a local template."
            : message,
        );
      } finally {
        if (activeIngestRef.current?.id === requestId) {
          activeIngestRef.current = null;
          setLoading(false);
        }
      }
    },
    [navigate, setIngestionResult, sources, state.settings.preferredModel, state.settings.preferredProvider],
  );

  const handleStopGeneration = useCallback(() => {
    const active = activeIngestRef.current;
    if (!active) return;
    active.controller.abort();
    activeIngestRef.current = null;
    setError(null);
    setLoading(false);
    textareaRef.current?.focus();
  }, []);

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

  const handleRunExample = useCallback(async () => {
    setLoadingExample(true);
    setError(null);
    try {
      const result = await analyzeExample();
      completeTrial(createExampleCompletedTrial(result));
      navigate("/results");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the example analysis.");
    } finally {
      setLoadingExample(false);
    }
  }, [completeTrial, navigate]);

  const autoResize = (el: HTMLTextAreaElement) => {
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  };

  if (state.trial?.status === "active") {
    return (
      <div className="home-center">
        <div className="fade-up" style={{ textAlign: "center" }}>
          <h1 style={{ fontSize: 38, fontWeight: 800, letterSpacing: 0, marginBottom: 12 }}>
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
        <h1 style={{ fontSize: 38, fontWeight: 800, letterSpacing: 0, marginBottom: 12, lineHeight: 1.1 }}>
          What do you want to test?
        </h1>
        <p style={{ color: "var(--gray-500)", fontSize: 16, maxWidth: 500, margin: "0 auto" }}>
          Compare a routine, product, or pattern you can keep consistent. Add research when it helps.
        </p>
      </div>

      <div className="path-grid fade-up fade-up-1">
        <button className="path-card" type="button" onClick={handleRunExample} disabled={loadingExample}>
          <strong>Run example</strong>
          <span>{loadingExample ? "Loading..." : "See a completed result with bundled data."}</span>
        </button>
        <button
          className="path-card"
          type="button"
          onClick={() => document.getElementById("template-start")?.scrollIntoView({ behavior: "smooth" })}
        >
          <strong>Start template</strong>
          <span>No API key. Lock labels, then check in daily.</span>
        </button>
        <button className="path-card" type="button" onClick={() => textareaRef.current?.focus()}>
          <strong>Ask question</strong>
          <span>Generate a protocol from your exact comparison.</span>
        </button>
      </div>

      <div className="preflight-box fade-up fade-up-2">
        <strong>Good fit:</strong> low-risk routines, cosmetic products, habits, tracking, or environmental changes.
        <span>Medication changes, urgent symptoms, invasive interventions, and diagnosis questions need a different path. If a plan touches a condition, medication, or symptoms, bring it to your clinician.</span>
      </div>

      <div className="fade-up fade-up-3" style={{ width: "100%", maxWidth: 680, marginBottom: 24 }}>
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
              accept=".txt,.md,.csv,.json"
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
              className={`chat-send${loading ? " chat-stop" : ""}`}
              aria-label={loading ? "Stop generation" : "Generate protocol"}
              onClick={loading ? handleStopGeneration : () => handleSubmit(query)}
              type="button"
            >
              {loading ? (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <rect x="4" y="4" width="8" height="8" rx="1.5" fill="currentColor" />
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <path d="M2 8h12M10 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </button>
          </div>
        </div>
        {error && (
          <p className="form-error" role="alert">{error}</p>
        )}
      </div>

      <details className="source-panel fade-up fade-up-4" open={sourceOpen} onToggle={(event) => setSourceOpen(event.currentTarget.open)}>
        <summary className="source-panel-summary">
          <span>Add research source</span>
          <small>Optional text, markdown, CSV, or JSON</small>
        </summary>
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
      </details>

      <div className="fade-up fade-up-4" style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center", marginTop: 20, maxWidth: 680 }}>
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

      <div id="template-start" className="fade-up fade-up-5" style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0, color: "var(--gray-400)", marginTop: 30, marginBottom: 12, textAlign: "center" }}>
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

function getProviderForRuntime(provider: AiProviderKind): AiProviderKind {
  if (isTauriRuntime() && provider === "openrouter") return "ollama";
  return provider;
}

function enrichIngestionResult(result: IngestionResult, sources: SourceDocument[]): IngestionResult {
  if (sources.length === 0 || (result.sources?.length ?? 0) > 0) return result;
  return {
    ...result,
    sources: sources.map((source, index) => ({
      source_id: `source-${index + 1}`,
      source_type: "text",
      title: source.name,
      locator: source.name,
      evidence_quality: result.evidence_quality,
      summary: result.source_summaries?.[index] ?? "User-provided source.",
      rationale: "Attached by the user before protocol generation.",
    })),
  };
}

function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}

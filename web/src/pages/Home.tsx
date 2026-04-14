import { useCallback, useRef, useState, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../lib/AppContext";
import { analyzeExample } from "../lib/api";
import { readSourceFile } from "../lib/sourceFiles";
import {
  createExampleCompletedTrial,
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
  const [sourceOpen, setSourceOpen] = useState(false);
  const [loadingExample, setLoadingExample] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { completeTrial, createExperiment } = useApp();

  const addSource = useCallback((name: string, content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;
    if (sources.some((source) => source.content === trimmed)) {
      setError("That source is already attached.");
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
      setError(null);
      const experiment = createExperiment({
        query: trimmed,
        documents: sources.map((source) => source.content),
        sourceNames: sources.map((source) => source.name),
      });
      navigate(`/experiments/${experiment.id}`);
    },
    [createExperiment, navigate, sources],
  );

  const handleFileUpload = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;
      const input = event.target;
      void (async () => {
        try {
          addSource(file.name, await readSourceFile(file));
        } catch (uploadError) {
          setError(errorMessage(uploadError));
        } finally {
          input.value = "";
        }
      })();
    },
    [addSource],
  );

  const handleAddPastedSource = useCallback(() => {
    addSource(sourceName(sourceText), sourceText);
    setSourceText("");
  }, [addSource, sourceText]);

  const handleTemplateStart = useCallback(
    (template: TrialTemplate) => {
      setError(null);
      const experiment = createExperiment({
        query: `Start ${template.name}`,
        ingestionResult: templateToIngestionResult(template),
        status: "ready_to_lock",
      });
      navigate(`/experiments/${experiment.id}`);
    },
    [createExperiment, navigate],
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
            aria-label="Experiment question"
          />
          <div className="chat-actions">
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,.csv,.json,.pdf,application/pdf"
              style={{ display: "none" }}
              onChange={handleFileUpload}
            />
            <button
              className="chat-action-btn"
              aria-label="Upload source file"
              onClick={() => fileInputRef.current?.click()}
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
              type="button"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path d="M2 8h12M10 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
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
          <small>Text, markdown, CSV, JSON, PDF, or article URL</small>
        </summary>
        <div className="source-panel-header">
          <div>
            <h2>Source Material</h2>
            <p>Paste article URLs, abstracts, notes, claims, or product details. Sources stay separate from your question.</p>
          </div>
          <button
            className="btn btn-s btn-sm"
            onClick={handleAddPastedSource}
            disabled={!sourceText.trim()}
          >
            Add Source
          </button>
        </div>
        <textarea
          className="source-textarea"
          placeholder="Paste source text or an article URL here..."
          value={sourceText}
          onChange={(e) => setSourceText(e.target.value)}
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

function sourceName(content: string): string {
  const trimmed = content.trim();
  if (!isLikelyUrl(trimmed)) return "Pasted source";
  try {
    return new URL(trimmed).hostname;
  } catch {
    return "Source link";
  }
}

function isLikelyUrl(content: string): boolean {
  return /^https?:\/\/\S+$/i.test(content);
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) return error.message;
  if (typeof error === "string" && error.trim()) return error;
  return "Could not generate a protocol.";
}

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useApp } from "../lib/AppContext";
import { ingestExperimentStream } from "../lib/api";
import {
  enrichIngestionResultWithSources,
  messageFromIngestionResult,
} from "../lib/experiments";
import { isTauriRuntime } from "../lib/runtime";
import type { AiProviderKind, ExperimentConversation, ExperimentMessage } from "../lib/types";

const inflightExperimentControllers = new Map<string, AbortController>();

export function ExperimentChat() {
  const { experimentId } = useParams();
  const navigate = useNavigate();
  const {
    state,
    appendExperimentMessage,
    setExperimentStatus,
    setExperimentResult,
    reviseExperimentRequest,
    markExperimentRead,
    setCurrentExperiment,
    setIngestionResult,
  } = useApp();
  const [reply, setReply] = useState("");
  const experiment = useMemo(
    () => state.experiments.find((item) => item.id === experimentId) ?? null,
    [experimentId, state.experiments],
  );

  useEffect(() => {
    if (!experimentId) return undefined;
    setCurrentExperiment(experimentId);
    markExperimentRead(experimentId);
    return () => setCurrentExperiment(null);
  }, [experimentId, markExperimentRead, setCurrentExperiment]);

  useEffect(() => {
    if (!experiment || experiment.status !== "draft" || experiment.ingestionResult) return;
    if (inflightExperimentControllers.has(experiment.id)) return;
    const controller = new AbortController();
    inflightExperimentControllers.set(experiment.id, controller);
    setExperimentStatus(experiment.id, "generating");
    appendExperimentMessage(experiment.id, {
      role: "trace",
      content: "Starting experiment setup.",
      status: "streaming",
    });

    void (async () => {
      try {
        const result = await ingestExperimentStream(
          experiment.query,
          experiment.documents,
          state.settings.preferredModel || undefined,
          providerForRuntime(state.settings.preferredProvider),
          (event) => {
            if (event.type !== "trace") return;
            appendExperimentMessage(experiment.id, {
              role: "trace",
              content: event.message,
              status: "streaming",
            });
          },
          { signal: controller.signal, workflowId: experiment.workflowId },
        );
        const enriched = enrichIngestionResultWithSources(result, experiment.sourceNames);
        setExperimentResult(experiment.id, enriched);
        appendExperimentMessage(experiment.id, messageFromIngestionResult(enriched));
      } catch (error) {
        if (isAbortError(error) || controller.signal.aborted) {
          setExperimentStatus(experiment.id, "needs_review");
          appendExperimentMessage(experiment.id, {
            role: "assistant",
            content: "Setup stopped. Send another message when you want to continue.",
            status: "done",
          });
          return;
        }
        const message = errorMessage(error);
        setExperimentStatus(experiment.id, "error");
        appendExperimentMessage(experiment.id, {
          role: "assistant",
          content: message.includes("OPENROUTER_API_KEY")
            ? "Protocol generation needs an API key. You can still start from a local template."
            : message,
          status: "error",
        });
      } finally {
        if (inflightExperimentControllers.get(experiment.id) === controller) {
          inflightExperimentControllers.delete(experiment.id);
        }
      }
    })();
  }, [
    appendExperimentMessage,
    experiment,
    setExperimentResult,
    setExperimentStatus,
    state.settings.preferredModel,
    state.settings.preferredProvider,
  ]);

  const handleReviewProtocol = useCallback(() => {
    if (!experiment?.ingestionResult) return;
    setIngestionResult(experiment.ingestionResult, experiment.id);
    navigate("/protocol");
  }, [experiment, navigate, setIngestionResult]);

  const handleStop = useCallback(() => {
    if (!experiment) return;
    inflightExperimentControllers.get(experiment.id)?.abort();
  }, [experiment]);

  const handleReplySubmit = useCallback(
    (event: FormEvent) => {
      event.preventDefault();
      if (!experiment) return;
      const trimmed = reply.trim();
      if (!trimmed) return;
      appendExperimentMessage(experiment.id, {
        role: "user",
        content: trimmed,
        status: "done",
      });
      reviseExperimentRequest(
        experiment.id,
        `${experiment.query}\n\nUser follow-up: ${trimmed}`,
      );
      setReply("");
    },
    [appendExperimentMessage, experiment, reply, reviseExperimentRequest],
  );

  if (!experiment) {
    return (
      <div className="home-center">
        <div style={{ textAlign: "center" }}>
          <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: 0, marginBottom: 12 }}>
            Experiment not found
          </h1>
          <Link className="btn btn-p" to="/">
            Start New Experiment
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="experiment-chat-shell">
      <header className="experiment-chat-header">
        <div>
          <div className="experiment-chat-eyebrow">Experiment setup</div>
          <h1>{experiment.title}</h1>
        </div>
        <span className={`experiment-status experiment-status-${experiment.status}`}>
          {statusCopy(experiment.status)}
        </span>
      </header>

      <section className="experiment-chat-body" aria-label="Experiment conversation">
        {experiment.messages.map((message) => (
          <ExperimentMessageBubble
            key={message.id}
            message={message}
            experiment={experiment}
            onReviewProtocol={handleReviewProtocol}
          />
        ))}
      </section>

      <form className="experiment-chat-composer" onSubmit={handleReplySubmit}>
        <textarea
          value={reply}
          onChange={(event) => setReply(event.target.value)}
          placeholder={composerPlaceholder(experiment)}
          aria-label="Reply to experiment setup"
          rows={1}
          disabled={experiment.status === "generating"}
        />
        {experiment.status === "generating" ? (
          <button className="chat-send chat-stop" type="button" onClick={handleStop} aria-label="Stop generation">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="4" y="4" width="8" height="8" rx="1.5" fill="currentColor" />
            </svg>
          </button>
        ) : (
          <button className="chat-send" type="submit" aria-label="Send follow-up">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M2 8h12M10 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        )}
      </form>
    </div>
  );
}

function ExperimentMessageBubble({
  message,
  experiment,
  onReviewProtocol,
}: {
  message: ExperimentMessage;
  experiment: ExperimentConversation;
  onReviewProtocol: () => void;
}) {
  if (message.role === "trace") {
    return (
      <div className="experiment-trace-row">
        <span className="trace-dot" />
        <span>{message.content}</span>
      </div>
    );
  }

  return (
    <article className={`experiment-message ${message.role} ${message.status === "error" ? "error" : ""}`}>
      <div className="experiment-message-label">
        {message.role === "user" ? "You" : "PitGPT"}
      </div>
      <p>{message.content}</p>
      {(message.questions?.length ?? 0) > 0 && (
        <div className="follow-up-list">
          <h2>Follow-up questions</h2>
          <ol>
            {message.questions?.map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ol>
        </div>
      )}
      {experiment.status === "ready_to_lock" && message.ingestionResult && (
        <button className="btn btn-p" type="button" onClick={onReviewProtocol}>
          Review Protocol
        </button>
      )}
      {experiment.status === "active" && experiment.trialId && (
        <Link className="btn btn-p" to="/trial">
          Open Active Trial
        </Link>
      )}
    </article>
  );
}

function providerForRuntime(provider: AiProviderKind): AiProviderKind {
  if (isTauriRuntime() && provider === "openrouter") return "ollama";
  return provider;
}

function statusCopy(status: ExperimentConversation["status"]): string {
  if (status === "draft") return "Queued";
  if (status === "generating") return "Thinking";
  if (status === "needs_review") return "Needs answers";
  if (status === "ready_to_lock") return "Protocol ready";
  if (status === "blocked") return "Blocked";
  if (status === "active") return "Active";
  if (status === "completed") return "Completed";
  return "Needs attention";
}

function composerPlaceholder(experiment: ExperimentConversation): string {
  if (experiment.status === "generating") return "PitGPT is working...";
  if (experiment.status === "needs_review") return "Answer the follow-up questions...";
  if (experiment.status === "ready_to_lock") return "Add a change before reviewing, or open the protocol.";
  if (experiment.status === "blocked") return "Try a safer everyday routine or product comparison.";
  return "Add more detail...";
}

function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) return error.message;
  if (typeof error === "string" && error.trim()) return error;
  return "Could not set up this experiment.";
}

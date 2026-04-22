import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../lib/AppContext";
import { getWorkflowDemo, listWorkflows } from "../lib/api";
import type { WorkflowDefinition } from "../lib/types";

export function Workflows() {
  const navigate = useNavigate();
  const { createExperiment } = useApp();
  const [workflows, setWorkflows] = useState<WorkflowDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void listWorkflows()
      .then((items) => {
        if (!active) return;
        setWorkflows(items);
      })
      .catch((loadError) => {
        if (!active) return;
        setError(errorMessage(loadError));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function runDemo(workflowId: string): Promise<void> {
    setRunningId(workflowId);
    setError(null);
    try {
      const demo = await getWorkflowDemo(workflowId);
      const experiment = createExperiment({
        query: demo.query,
        workflowId: demo.workflow_id,
        documents: demo.documents,
        sourceNames: demo.documents.map((_, index) => `${demo.workflow_id}-source-${index + 1}.txt`),
      });
      navigate(`/experiments/${experiment.id}`);
    } catch (runError) {
      setError(errorMessage(runError));
    } finally {
      setRunningId(null);
    }
  }

  return (
    <div className="workflow-page">
      <header className="workflow-header fade-up">
        <p className="workflow-kicker">Curated Workflow Collection</p>
        <h1>MedGemma Workflows</h1>
        <p>
          Three restrained pathways for genomics and home-lab analysis. Each run keeps PitGPT
          safety limits intact and elevates clinician escalation when signals demand review.
        </p>
      </header>
      {loading ? <p className="workflow-loading">Loading workflows...</p> : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      <section className="workflow-grid" aria-label="Workflow demos">
        {workflows.map((workflow) => (
          <article
            className={`workflow-card theme-${workflow.ui.theme}`}
            key={workflow.id}
            aria-label={workflow.title}
          >
            <div className="workflow-art-wrap">
              <img src={workflow.ui.hero_asset} alt="" aria-hidden="true" />
            </div>
            <div className="workflow-card-body">
              <p className="workflow-subtitle">{workflow.ui.subtitle}</p>
              <h2>{workflow.title}</h2>
              <p>{workflow.ui.description}</p>
              <p className="workflow-objective">{workflow.objective}</p>
              <div className="workflow-meta">
                <span>Provider baseline: {workflow.recommended_provider}</span>
                <span>
                  Model baseline: {workflow.recommended_models[workflow.recommended_provider] || "auto"}
                </span>
              </div>
              <button
                className="btn btn-s workflow-launch-btn"
                type="button"
                disabled={runningId === workflow.id}
                onClick={() => {
                  void runDemo(workflow.id);
                }}
              >
                {runningId === workflow.id ? "Launching..." : "Run Demo"}
              </button>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) return error.message;
  if (typeof error === "string" && error.trim()) return error;
  return "Could not load workflows.";
}

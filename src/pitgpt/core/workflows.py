import re
from collections.abc import Mapping
from functools import lru_cache

import httpx
from pydantic import BaseModel, Field

from pitgpt.core.providers import ProviderKind
from pitgpt.core.settings import Settings
from pitgpt.core.shared import load_shared_json

WORKFLOWS_FILE = "workflows.json"
_WORKFLOW_PROVIDER_OVERRIDES = {
    ProviderKind.OPENROUTER: "PITGPT_WORKFLOW_MEDGEMMA_MODEL_OPENROUTER",
    ProviderKind.OLLAMA: "PITGPT_WORKFLOW_MEDGEMMA_MODEL_OLLAMA",
}


class WorkflowUI(BaseModel):
    subtitle: str
    description: str
    hero_asset: str
    theme: str


class WorkflowDemo(BaseModel):
    query: str
    documents: list[str] = Field(default_factory=list)


class WorkflowDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str
    objective: str
    prompt_scaffold: str
    recommended_provider: ProviderKind = ProviderKind.OPENROUTER
    recommended_models: dict[ProviderKind, str] = Field(default_factory=dict)
    ui: WorkflowUI
    demo: WorkflowDemo


class WorkflowDemoPayload(BaseModel):
    workflow_id: str
    query: str
    documents: list[str] = Field(default_factory=list)
    recommended_provider: ProviderKind
    recommended_model: str = ""


@lru_cache(maxsize=1)
def _workflow_index() -> dict[str, WorkflowDefinition]:
    data = load_shared_json(WORKFLOWS_FILE)
    if not isinstance(data, list):
        raise ValueError(f"{WORKFLOWS_FILE} must be a JSON array.")
    workflows = [WorkflowDefinition.model_validate(item) for item in data]
    return {workflow.id: workflow for workflow in workflows}


def list_workflows() -> list[WorkflowDefinition]:
    return list(_workflow_index().values())


def get_workflow(workflow_id: str) -> WorkflowDefinition | None:
    return _workflow_index().get(workflow_id)


def workflow_demo_payload(workflow: WorkflowDefinition) -> WorkflowDemoPayload:
    return WorkflowDemoPayload(
        workflow_id=workflow.id,
        query=workflow.demo.query,
        documents=workflow.demo.documents,
        recommended_provider=workflow.recommended_provider,
        recommended_model=workflow.recommended_models.get(workflow.recommended_provider, ""),
    )


def build_workflow_query(query: str, workflow: WorkflowDefinition | None) -> str:
    if workflow is None:
        return query.strip()
    return (
        f"Workflow mode: {workflow.title}\n"
        f"Workflow objective: {workflow.objective}\n"
        "Workflow constraints:\n"
        f"{workflow.prompt_scaffold}\n"
        "When uncertain, prefer manual_review_before_protocol over "
        "overconfident protocol generation.\n"
        "User request:\n"
        f"{query.strip()}"
    )


def resolve_workflow_model(
    workflow: WorkflowDefinition | None,
    provider: ProviderKind,
    requested_model: str | None,
    fallback_model: str,
    settings: Settings,
    env: Mapping[str, str],
) -> tuple[str, str | None]:
    if requested_model:
        return requested_model, None
    if workflow is None:
        return fallback_model, None
    candidate = _workflow_model_candidate(workflow, provider, settings, env)
    if not candidate:
        return fallback_model, (
            f"Workflow {workflow.id} did not provide a MedGemma default for {provider.value}. "
            f"Using fallback model {fallback_model}."
        )
    if provider == ProviderKind.OLLAMA and not _ollama_model_exists(
        settings.ollama_base_url, candidate
    ):
        return fallback_model, (
            f"Workflow {workflow.id} requested {candidate}, but that Ollama model was not found. "
            f"Using fallback model {fallback_model}."
        )
    return candidate, None


def _workflow_model_candidate(
    workflow: WorkflowDefinition,
    provider: ProviderKind,
    settings: Settings,
    env: Mapping[str, str],
) -> str:
    specific = env.get(_workflow_env_key(workflow.id, provider), "").strip()
    if specific:
        return specific
    provider_override = env.get(_WORKFLOW_PROVIDER_OVERRIDES.get(provider, ""), "").strip()
    if provider_override:
        return provider_override
    if provider == ProviderKind.OPENROUTER and settings.workflow_medgemma_model_openrouter:
        return settings.workflow_medgemma_model_openrouter
    if provider == ProviderKind.OLLAMA and settings.workflow_medgemma_model_ollama:
        return settings.workflow_medgemma_model_ollama
    return workflow.recommended_models.get(provider, "").strip()


def _workflow_env_key(workflow_id: str, provider: ProviderKind) -> str:
    normalized_id = re.sub(r"[^A-Za-z0-9]+", "_", workflow_id).strip("_").upper()
    return f"PITGPT_WORKFLOW_MODEL_{normalized_id}_{provider.value.upper()}"


def _ollama_model_exists(base_url: str, model_name: str) -> bool:
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        with httpx.Client(timeout=1.0) as client:
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError, ValueError):
        return False
    tags = payload.get("models", [])
    if not isinstance(tags, list):
        return False
    names = {
        str(item.get("name", "")).strip()
        for item in tags
        if isinstance(item, dict) and item.get("name")
    }
    return model_name in names

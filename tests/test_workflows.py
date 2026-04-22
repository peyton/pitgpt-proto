from pitgpt.core.providers import ProviderKind
from pitgpt.core.settings import load_settings
from pitgpt.core.workflows import (
    build_workflow_query,
    get_workflow,
    list_workflows,
    resolve_workflow_model,
    workflow_demo_payload,
)


def test_workflow_catalog_is_loaded() -> None:
    ids = {workflow.id for workflow in list_workflows()}
    assert "genotype_routine_hypothesis" in ids
    assert "multiomics_crossover_designer" in ids
    assert "adverse_signal_clinician_escalation" in ids


def test_build_workflow_query_wraps_user_prompt() -> None:
    workflow = get_workflow("genotype_routine_hypothesis")
    assert workflow is not None
    wrapped = build_workflow_query("Compare two routines", workflow)
    assert "Workflow mode:" in wrapped
    assert "Compare two routines" in wrapped


def test_workflow_demo_payload_has_id_and_documents() -> None:
    workflow = get_workflow("multiomics_crossover_designer")
    assert workflow is not None
    demo = workflow_demo_payload(workflow)
    assert demo.workflow_id == "multiomics_crossover_designer"
    assert len(demo.documents) > 0


def test_resolve_workflow_model_uses_provider_defaults() -> None:
    workflow = get_workflow("genotype_routine_hypothesis")
    assert workflow is not None
    settings = load_settings({})
    model, warning = resolve_workflow_model(
        workflow=workflow,
        provider=ProviderKind.OPENROUTER,
        requested_model=None,
        fallback_model="anthropic/claude-sonnet-4",
        settings=settings,
        env={},
    )
    assert model == "google/medgemma-1.5-4b-it"
    assert warning is None
